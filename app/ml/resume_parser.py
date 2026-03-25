"""
Resume PDF parser — extracts text from an uploaded PDF and
maps it against a skills taxonomy using keyword matching.
Falls back to regexp heuristics for contact info / experience years.
"""
from __future__ import annotations
import re
import io
from typing import Any

# Try pdfminer first, then pypdf as fallback
def _extract_text(pdf_bytes: bytes) -> str:
    # Attempt 1: pdfminer.six — most reliable for text-based PDFs
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(io.BytesIO(pdf_bytes))
        if text and text.strip():
            return text
    except Exception:
        pass

    # Attempt 2: pypdf (lighter fallback)
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(pages)
        if text and text.strip():
            return text
    except Exception:
        pass

    return ""

# Comprehensive skills taxonomy
SKILLS_TAXONOMY: list[str] = [
    # Programming Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Swift",
    "Kotlin", "Ruby", "PHP", "Scala", "R", "MATLAB", "Bash", "Shell",
    # ML / AI
    "Machine Learning", "Deep Learning", "NLP", "Natural Language Processing",
    "Computer Vision", "Reinforcement Learning", "TensorFlow", "PyTorch", "Keras",
    "Scikit-learn", "XGBoost", "LightGBM", "Transformers", "BERT", "GPT",
    "Hugging Face", "LangChain", "RAG", "Vector Database", "Embedding",
    # Data
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "Pandas", "NumPy", "Spark", "Hadoop", "Kafka", "Airflow", "dbt",
    "BigQuery", "Snowflake", "Databricks", "ETL", "Data Pipeline",
    # Cloud & DevOps
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "CI/CD",
    "GitHub Actions", "Jenkins", "Ansible", "Linux", "Nginx",
    # Web
    "React", "Vue", "Angular", "Node.js", "FastAPI", "Flask", "Django",
    "REST API", "GraphQL", "HTML", "CSS", "Tailwind",
    # Other
    "Agile", "Scrum", "Git", "JIRA", "Figma", "Tableau", "Power BI",
    "A/B Testing", "Statistics", "Probability", "Linear Algebra",
    "System Design", "Microservices", "Event-Driven Architecture",
]

# Categories for grouping matched skills in the UI breakdown
SKILL_CATEGORIES: dict[str, list[str]] = {
    "Programming Languages": [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
        "Swift", "Kotlin", "Ruby", "PHP", "Scala", "R", "MATLAB", "Bash", "Shell",
    ],
    "AI / ML": [
        "Machine Learning", "Deep Learning", "NLP", "Natural Language Processing",
        "Computer Vision", "Reinforcement Learning", "TensorFlow", "PyTorch", "Keras",
        "Scikit-learn", "XGBoost", "LightGBM", "Transformers", "BERT", "GPT",
        "Hugging Face", "LangChain", "RAG", "Vector Database", "Embedding",
    ],
    "Data & Databases": [
        "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "Pandas", "NumPy", "Spark", "Hadoop", "Kafka", "Airflow", "dbt",
        "BigQuery", "Snowflake", "Databricks", "ETL", "Data Pipeline",
    ],
    "Cloud & DevOps": [
        "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "CI/CD",
        "GitHub Actions", "Jenkins", "Ansible", "Linux", "Nginx",
    ],
    "Web & APIs": [
        "React", "Vue", "Angular", "Node.js", "FastAPI", "Flask", "Django",
        "REST API", "GraphQL", "HTML", "CSS", "Tailwind",
    ],
    "Soft / Other": [
        "Agile", "Scrum", "Git", "JIRA", "Figma", "Tableau", "Power BI",
        "A/B Testing", "Statistics", "Probability", "Linear Algebra",
        "System Design", "Microservices", "Event-Driven Architecture",
    ],
}


def parse_resume(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Parse a PDF resume and return a structured breakdown dict:
        {
          "raw_text_preview": str,
          "skills_found": [str, ...],
          "categories": {category: [str, ...], ...},
          "experience_years": int | None,
          "emails": [str, ...],
          "word_count": int,
          "skill_count": int,
        }
    """
    text = _extract_text(pdf_bytes)
    if not text.strip():
        return {"error": "Could not extract text from PDF. Make sure it's a text-based PDF, not a scan."}

    text_lower = text.lower()
    word_count = len(text.split())

    # Match skills (case-insensitive)
    skills_found: list[str] = []
    for skill in SKILLS_TAXONOMY:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_lower):
            skills_found.append(skill)

    # Group by category
    cat_breakdown: dict[str, list[str]] = {}
    for cat, cat_skills in SKILL_CATEGORIES.items():
        matched = [s for s in cat_skills if s in skills_found]
        if matched:
            cat_breakdown[cat] = matched

    # Extract experience years (e.g. "5+ years", "3 years of experience")
    exp_match = re.search(r"(\d+)\s*\+?\s*years?\s*(?:of\s+)?(?:experience|exp)", text_lower)
    experience_years = int(exp_match.group(1)) if exp_match else None

    # Extract email addresses
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)

    return {
        "raw_text_preview": text[:400].strip(),
        "skills_found": skills_found,
        "categories": cat_breakdown,
        "experience_years": experience_years,
        "emails": emails[:3],
        "word_count": word_count,
        "skill_count": len(skills_found),
    }
