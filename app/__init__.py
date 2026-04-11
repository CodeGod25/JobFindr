"""Flask application factory for JobFindr."""

import os
import json
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from .models import db, User, Job
from .routes.auth import auth_bp
from .routes.jobs import jobs_bp
from .routes.profile import profile_bp
from .routes.applications import apps_bp
from .routes.recommendations import recs_bp
from .routes.recruiter import recruiter_bp
from .routes.oauth import oauth_bp, init_oauth
from .ml.recommender import JobRecommender


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Check if running on Vercel (serverless environment)
    is_vercel = os.environ.get("VERCEL", False)

    # Configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Use in-memory database for Vercel, file-based for local
    if is_vercel:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
            "SQLALCHEMY_DATABASE_URI",
            "sqlite:///jobfindr.db"
        )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # OAuth Configuration
    app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID", "")
    app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    app.config["LINKEDIN_CLIENT_ID"] = os.environ.get("LINKEDIN_CLIENT_ID", "")
    app.config["LINKEDIN_CLIENT_SECRET"] = os.environ.get("LINKEDIN_CLIENT_SECRET", "")

    # Initialize database
    db.init_app(app)

    # Initialize OAuth (with error handling)
    try:
        init_oauth(app)
    except Exception as e:
        print(f"Warning: OAuth initialization failed: {e}")

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(jobs_bp)  # No prefix - landing page is at root /
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(apps_bp, url_prefix="/applications")
    app.register_blueprint(recs_bp, url_prefix="/recommendations")
    app.register_blueprint(recruiter_bp, url_prefix="/recruiter")
    app.register_blueprint(oauth_bp, url_prefix="/oauth")

    # Create database tables and seed if necessary
    try:
        with app.app_context():
            db.create_all()
            _seed_database()
            # Initialize and attach recommender after seeding
            app.recommender = JobRecommender()
    except Exception as e:
        print(f"Warning: App initialization error: {e}")
        # Fallback recommender if DB fails
        app.recommender = JobRecommender()

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Seeding
# ─────────────────────────────────────────────────────────────────────────────

def _seed_database():
    """
    Seed the database on first boot.

    Job priority:
      1. data_ingestion/job_descriptions.csv  (Kaggle, ~500 real jobs)
      2. app/data/jobs.json                   (15 curated fallback jobs)

    Users always come from app/data/users.json + hardcoded recruiter.
    """
    if User.query.first():
        return  # Already seeded

    print("Seeding database...")
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    # ── Jobs ─────────────────────────────────────────────────────────────────
    kaggle_csv = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data_ingestion", "job_descriptions.csv")
    )
    if os.path.exists(kaggle_csv):
        _seed_jobs_from_kaggle(kaggle_csv, limit=500)
    else:
        print("Kaggle CSV not found — using jobs.json (15 curated jobs).")
        _seed_jobs_from_json(data_dir)

    # ── Users ─────────────────────────────────────────────────────────────────
    _seed_users(data_dir)

    db.session.commit()
    print("Database seeding completed.")


def _seed_jobs_from_kaggle(csv_path: str, limit: int = 500):
    """Seed jobs from the Kaggle job_descriptions.csv."""
    try:
        import pandas as pd
    except ImportError:
        print("pandas not installed — falling back to jobs.json.")
        _seed_jobs_from_json(os.path.join(os.path.dirname(__file__), "data"))
        return

    print(f"Seeding from Kaggle CSV ({limit} jobs)...")

    # Column aliases — handles multiple versions of the Kaggle dataset
    def _pick(df, aliases, default=""):
        for col in aliases:
            if col in df.columns:
                return df[col].fillna(default).astype(str)
        return pd.Series([default] * len(df), index=df.index)

    DEPT_MAP = {
        "AI Research":      ["ai research", "artificial intelligence"],
        "Machine Learning": ["machine learning", "ml engineer", "computer vision", "nlp", "pytorch", "tensorflow"],
        "Data Science":     ["data scientist", "data science", "analytics", "quantitative"],
        "Data Engineering": ["data engineer", "spark", "kafka", "etl", "databricks", "airflow"],
        "MLOps":            ["mlops", "devops", "ci/cd", "kubernetes", "docker"],
        "Backend":          ["backend", "back-end", "microservices", "api", "java", "golang"],
        "Full-Stack":       ["full stack", "fullstack", "react", "angular", "vue", "node"],
        "Frontend":         ["frontend", "front-end", "ui engineer", "ios", "android"],
        "Design":           ["designer", "ux", "figma", "product design"],
        "Product":          ["product manager", "product owner", "pm"],
        "Security":         ["security", "cybersecurity", "zero trust"],
        "Platform":         ["platform", "cloud", "aws", "azure", "gcp", "terraform"],
    }

    def _infer_dept(title, skills):
        combined = (str(title) + " " + str(skills)).lower()
        for dept, keywords in DEPT_MAP.items():
            if any(kw in combined for kw in keywords):
                return dept
        return "Engineering"

    try:
        df = pd.read_csv(csv_path, nrows=limit * 15, encoding="utf-8",
                         on_bad_lines="skip", low_memory=False)
    except Exception:
        try:
            df = pd.read_csv(csv_path, nrows=limit * 15, encoding="latin-1",
                             on_bad_lines="skip", low_memory=False)
        except Exception as e:
            print(f"Could not read Kaggle CSV: {e}. Falling back to jobs.json.")
            _seed_jobs_from_json(os.path.join(os.path.dirname(__file__), "data"))
            return

    titles    = _pick(df, ["Job Title", "title", "job_title", "Position"])
    companies = _pick(df, ["Company", "company", "Employer", "Company Name"], "Unknown")
    locations = _pick(df, ["location", "Location", "Job Location"], "Remote")
    descs     = _pick(df, ["Job Description", "description", "job_description"])
    skills_s  = _pick(df, ["skills", "Skills", "Key Skills", "key_skills"])
    type_s    = _pick(df, ["Job Type", "job_type", "Employment Type"], "Full-time")

    df2 = pd.DataFrame({
        "title": titles, "company": companies, "location": locations,
        "description": descs, "skills_raw": skills_s, "type_raw": type_s,
    })
    df2 = df2[
        (df2["title"].str.strip() != "") &
        (df2["title"] != "nan") &
        (df2["description"].str.len() > 50)
    ]
    df2 = df2.sample(n=min(len(df2), limit), random_state=42)

    count = 0
    for _, row in df2.iterrows():
        skills_list = [s.strip() for s in str(row["skills_raw"]).split(",")
                       if s.strip() and s.strip().lower() != "nan"][:15]
        jtype = str(row["type_raw"]).strip()
        if not jtype or jtype == "nan":
            jtype = "Full-time"
        db.session.add(Job(
            title=str(row["title"])[:200],
            company=str(row["company"])[:200],
            location=str(row["location"])[:200],
            description=str(row["description"])[:4000],
            skills=skills_list,
            dept=_infer_dept(row["title"], row["skills_raw"]),
            type=jtype[:50],
            salary_min=0,
            salary_max=0,
            posted_at="",
            source="kaggle",
        ))
        count += 1

    print(f"  Added {count} Kaggle jobs.")


def _seed_jobs_from_json(data_dir: str):
    """Fallback: seed from the 15-job curated jobs.json."""
    jobs_path = os.path.join(data_dir, "jobs.json")
    if not os.path.exists(jobs_path):
        return
    with open(jobs_path, encoding="utf-8") as f:
        jobs_data = json.load(f)
    for j in jobs_data:
        db.session.add(Job(
            title=j["title"], company=j["company"], location=j["location"],
            type=j["type"], dept=j["dept"], salary_min=j["salary_min"],
            salary_max=j["salary_max"], description=j["description"],
            posted_at=j["posted_at"], skills=j["skills"],
            source=j.get("source", "local"),
        ))
    print(f"  Added {len(jobs_data)} curated jobs from jobs.json.")


def _seed_users(data_dir: str):
    """Seed demo users from users.json + hardcoded recruiter."""
    users_path = os.path.join(data_dir, "users.json")
    if os.path.exists(users_path):
        with open(users_path, encoding="utf-8") as f:
            users_data = json.load(f)
        for u in users_data:
            db.session.add(User(
                name=u["name"], email=u["email"],
                password_hash=generate_password_hash(u.get("password", "password123")),
                title=u["title"], bio=u["bio"], location=u["location"],
                experience_years=u["experience_years"], avatar=u.get("avatar", ""),
                skills=u["skills"], is_recruiter=False,
            ))

    db.session.add(User(
        name="Sarah Lin",
        email="recruiter@jobfindr.ai",
        password_hash=generate_password_hash("recruit123"),
        title="Senior Talent Acquisition",
        bio="Recruiting the best engineering talent for JobFindr.",
        location="San Francisco, CA",
        experience_years=8,
        is_recruiter=True,
        skills=["Talent Acquisition", "Technical Recruiting", "HR Strategy"],
    ))
    print("  Demo users seeded.")
