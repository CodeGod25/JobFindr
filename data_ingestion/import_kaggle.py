"""
JobFindr — Kaggle Job Description Dataset Importer
====================================================
Downloads and imports up to `limit` real job listings from the Kaggle
"Job Description Dataset" into the local SQLite database.

Dataset: https://www.kaggle.com/datasets/ravindrasinghrana/job-description-dataset
CSV file: job_descriptions.csv  (place it in this directory)

Usage:
    cd data_ingestion
    python import_kaggle.py                  # imports 500 jobs (default)
    python import_kaggle.py --limit 1000     # imports 1000 jobs
    python import_kaggle.py --clear          # clears existing jobs first, then imports
"""

import os
import sys
import re
import argparse

# ── Path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from app import create_app
from app.models import db, Job


# ── Column aliases ───────────────────────────────────────────────────────────
# The Kaggle CSV uses various column names depending on version/download method.
# We try each alias in order until we find a match.
TITLE_COLS    = ["Job Title", "title", "job_title", "Position"]
COMPANY_COLS  = ["Company", "company", "Employer", "Company Name", "company_name"]
LOCATION_COLS = ["location", "Location", "Job Location", "job_location"]
DESC_COLS     = ["Job Description", "description", "job_description", "Description"]
SKILLS_COLS   = ["skills", "Skills", "Key Skills", "key_skills", "Required Skills"]
DEPT_COLS     = ["Role Category", "role_category", "Functional Area", "functional_area",
                 "Industry", "industry", "Department"]
TYPE_COLS     = ["Job Type", "job_type", "Employment Type", "employment_type"]


def _pick(df: pd.DataFrame, aliases: list, default="") -> pd.Series:
    """Return the first matching column from `aliases`, or a constant Series."""
    for col in aliases:
        if col in df.columns:
            return df[col].fillna(default).astype(str)
    return pd.Series([default] * len(df), index=df.index)


# ── Dept inference (fallback when no dept column present) ───────────────────
DEPT_KEYWORDS = {
    "AI Research":      ["ai research", "artificial intelligence", "deep learning research"],
    "Machine Learning": ["machine learning", "ml engineer", "computer vision", "nlp", "pytorch", "tensorflow"],
    "Data Science":     ["data scientist", "data science", "analytics", "statistical", "quantitative"],
    "Data Engineering": ["data engineer", "spark", "kafka", "pipeline", "etl", "databricks", "airflow"],
    "MLOps":            ["mlops", "devops", "ci/cd", "kubernetes", "docker", "infrastructure"],
    "Backend":          ["backend", "back-end", "api", "server", "microservices", "golang", "ruby", "java"],
    "Full-Stack":       ["full stack", "full-stack", "fullstack", "react", "angular", "vue", "node"],
    "Frontend":         ["frontend", "front-end", "ui engineer", "ios", "android", "swift", "kotlin"],
    "Design":           ["designer", "product design", "ux", "ui/ux", "figma"],
    "Product":          ["product manager", "product owner", "pm", "roadmap"],
    "Security":         ["security", "cybersecurity", "zero trust", "cryptography"],
    "Platform":         ["platform", "cloud", "aws", "azure", "gcp", "terraform"],
}

def _infer_dept(title: str, skills: str) -> str:
    combined = (title + " " + skills).lower()
    for dept, keywords in DEPT_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return dept
    return "Engineering"


# ── Salary extraction ────────────────────────────────────────────────────────
_SALARY_RE = re.compile(r"\$?([\d,]+)[kK]?\s*[-–]\s*\$?([\d,]+)[kK]?")

def _parse_salary(text: str):
    """Return (salary_min, salary_max) in whole dollars, or (0, 0)."""
    m = _SALARY_RE.search(str(text))
    if not m:
        return 0, 0
    lo = int(m.group(1).replace(",", ""))
    hi = int(m.group(2).replace(",", ""))
    # Detect k-notation
    if lo < 1000:
        lo *= 1000
    if hi < 1000:
        hi *= 1000
    return lo, hi


# ── Main import function ─────────────────────────────────────────────────────
def run_import(csv_path: str, limit: int = 500, clear: bool = False):
    """
    Import `limit` jobs from the Kaggle CSV into the SQLite database.

    Args:
        csv_path: Absolute or relative path to job_descriptions.csv
        limit:    Maximum number of jobs to import (default 500)
        clear:    If True, delete existing Kaggle-sourced jobs before import
    """
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV not found at: {csv_path}")
        print()
        print("How to get it:")
        print("  1. Go to https://www.kaggle.com/datasets/ravindrasinghrana/job-description-dataset")
        print("  2. Click Download")
        print(f"  3. Place job_descriptions.csv in: {os.path.dirname(csv_path)}")
        return False

    # ── Read CSV ─────────────────────────────────────────────────────────────
    print(f"Reading CSV: {csv_path}")
    print(f"  (reading up to {limit * 15} rows for sampling {limit})...")
    try:
        df = pd.read_csv(
            csv_path,
            nrows=limit * 15,   # over-read so we can sample after filtering
            encoding="utf-8",
            on_bad_lines="skip",
            low_memory=False,
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            csv_path,
            nrows=limit * 15,
            encoding="latin-1",
            on_bad_lines="skip",
            low_memory=False,
        )
    except Exception as e:
        print(f"ERROR reading CSV: {e}")
        return False

    print(f"  Columns found: {list(df.columns)}")
    print(f"  Total rows read: {len(df)}")

    # ── Extract columns ───────────────────────────────────────────────────────
    titles    = _pick(df, TITLE_COLS)
    companies = _pick(df, COMPANY_COLS, "Unknown Company")
    locations = _pick(df, LOCATION_COLS, "Remote")
    descs     = _pick(df, DESC_COLS)
    skills_s  = _pick(df, SKILLS_COLS)
    dept_s    = _pick(df, DEPT_COLS)
    type_s    = _pick(df, TYPE_COLS, "Full-time")

    # Salary is often in the description or a dedicated column
    sal_cols  = [c for c in df.columns if "salary" in c.lower() or "pay" in c.lower()]
    sal_raw   = df[sal_cols[0]].fillna("").astype(str) if sal_cols else pd.Series([""] * len(df))

    # ── Build structured DataFrame ────────────────────────────────────────────
    structured = pd.DataFrame({
        "title":    titles,
        "company":  companies,
        "location": locations,
        "description": descs,
        "skills_raw":  skills_s,
        "dept_raw":    dept_s,
        "type_raw":    type_s,
        "sal_raw":     sal_raw,
    })

    # Drop rows with empty title or description
    structured = structured[
        (structured["title"].str.strip() != "") &
        (structured["title"] != "nan") &
        (structured["description"].str.len() > 50)
    ]

    # Sample `limit` rows randomly
    structured = structured.sample(n=min(len(structured), limit), random_state=42)
    print(f"  Rows after filtering & sampling: {len(structured)}")

    if len(structured) == 0:
        print("ERROR: No valid rows found. Check CSV columns.")
        return False

    # ── Import into DB ────────────────────────────────────────────────────────
    app = create_app()
    with app.app_context():
        db.create_all()

        if clear:
            n_deleted = Job.query.filter_by(source="kaggle").delete()
            db.session.commit()
            print(f"  Cleared {n_deleted} existing Kaggle jobs from DB.")

        print(f"Importing {len(structured)} jobs into database...")
        imported = 0
        for _, row in structured.iterrows():
            skills_list = [
                s.strip() for s in str(row["skills_raw"]).split(",")
                if s.strip() and s.strip().lower() != "nan"
            ][:15]  # cap at 15 skills per job

            sal_min, sal_max = _parse_salary(row["sal_raw"])

            # Infer dept from title+skills if no dept column available
            dept = str(row["dept_raw"]).strip()
            if not dept or dept == "nan" or dept == "Unknown":
                dept = _infer_dept(str(row["title"]), str(row["skills_raw"]))

            # Normalise job type
            jtype = str(row["type_raw"]).strip()
            if not jtype or jtype == "nan":
                jtype = "Full-time"

            job = Job(
                title=str(row["title"])[:200],
                company=str(row["company"])[:200],
                location=str(row["location"])[:200],
                description=str(row["description"])[:4000],
                skills=skills_list,
                dept=dept[:100],
                type=jtype[:50],
                salary_min=sal_min,
                salary_max=sal_max,
                posted_at="",
                source="kaggle",
            )
            db.session.add(job)
            imported += 1

        db.session.commit()
        total_jobs = Job.query.count()
        print(f"\n✅ Import complete!")
        print(f"   Imported: {imported} Kaggle jobs")
        print(f"   Total jobs in DB: {total_jobs}")
        print()
        print("Next step: restart the Flask app — it will pick up the new data automatically.")
    return True


# ── CLI entry-point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Kaggle job data into JobFindr DB")
    parser.add_argument("--limit", type=int, default=500,
                        help="Max jobs to import (default: 500)")
    parser.add_argument("--clear", action="store_true",
                        help="Clear existing Kaggle jobs before import")
    parser.add_argument("--csv", type=str, default="",
                        help="Path to CSV (default: same directory as this script)")
    args = parser.parse_args()

    csv_path = args.csv or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "job_descriptions.csv"
    )
    run_import(csv_path, limit=args.limit, clear=args.clear)
