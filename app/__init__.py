"""
Flask Application Factory for JobFindr — Phase 2.
Uses SQLAlchemy for persistence and seeds DB from jobs.json / users.json
on first run.
"""

import json
import os
from typing import Optional
from flask import Flask
from .models import db, User, Job, Application
from .ml.recommender import JobRecommender

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

recommender: Optional[JobRecommender] = None


def create_app() -> Flask:
    global recommender

    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key = os.environ.get("SECRET_KEY", "jobfindr-secret-key-change-in-production")

    # ── OAuth credentials from environment / .env ────────────────────────
    app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID", "")
    app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    app.config["LINKEDIN_CLIENT_ID"] = os.environ.get("LINKEDIN_CLIENT_ID", "")
    app.config["LINKEDIN_CLIENT_SECRET"] = os.environ.get("LINKEDIN_CLIENT_SECRET", "")

    # ── SQLAlchemy config ────────────────────────────────────────────────
    # On Vercel, the filesystem is read-only except /tmp
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        db_path = "/tmp/jobfindr.db"
    else:
        db_path = os.path.join(os.path.dirname(__file__), "data", "jobfindr.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        _seed_if_empty()

    # ── ML Engine (reads from DB via jobs_as_dicts()) ────────────────────
    with app.app_context():
        recommender = JobRecommender()
    app.recommender = recommender  # type: ignore[attr-defined]

    # ── Blueprints ───────────────────────────────────────────────────────
    from .routes.auth import auth_bp
    from .routes.jobs import jobs_bp
    from .routes.recommendations import recs_bp
    from .routes.applications import apps_bp
    from .routes.profile import profile_bp
    from .routes.recruiter import recruiter_bp
    from .routes.oauth import oauth_bp, init_oauth

    app.register_blueprint(auth_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(recs_bp)
    app.register_blueprint(apps_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(oauth_bp)

    # Initialise Authlib OAuth clients
    init_oauth(app)

    return app


def _seed_if_empty():
    """Seed DB from JSON files if tables are empty (first-run only)."""
    from werkzeug.security import generate_password_hash

    data_dir = os.path.join(os.path.dirname(__file__), "data")

    # ── Seed Jobs ────────────────────────────────────────────────────────
    if Job.query.count() == 0:
        jobs_path = os.path.join(data_dir, "jobs.json")
        with open(jobs_path, encoding="utf-8") as f:
            raw_jobs = json.load(f)
        for jd in raw_jobs:
            job = Job(
                id=jd["id"],
                title=jd["title"],
                company=jd["company"],
                location=jd.get("location", ""),
                type=jd.get("type", "Full-time"),
                dept=jd.get("dept", "Engineering"),
                salary_min=jd.get("salary_min", 0),
                salary_max=jd.get("salary_max", 0),
                description=jd.get("description", ""),
                posted_at=jd.get("posted_at", ""),
                source="local",
            )
            job.skills = jd.get("skills", [])
            db.session.add(job)
        db.session.commit()
        print(f"[JobFindr] Seeded {len(raw_jobs)} jobs into SQLite.")

    # ── Seed Users ───────────────────────────────────────────────────────
    if User.query.count() == 0:
        users_path = os.path.join(data_dir, "users.json")
        with open(users_path, encoding="utf-8") as f:
            raw_users = json.load(f)
        for ud in raw_users:
            user = User(
                id=ud["id"],
                name=ud["name"],
                email=ud["email"],
                password_hash=generate_password_hash(ud["password"]),
                title=ud.get("title", ""),
                bio=ud.get("bio", ""),
                location=ud.get("location", ""),
                experience_years=ud.get("experience_years", 0),
                avatar=ud.get("avatar", ""),
            )
            user.skills = ud.get("skills", [])
            user.applications = ud.get("applications", [])
            user.saved_jobs = ud.get("saved_jobs", [])
            db.session.add(user)

        # Seed some sample applications for user 1
        db.session.flush()
        sample_apps = [
            Application(user_id=1, job_id=1, status="interview",
                        applied_date="Mar 18, 2026", contact="Sarah L. (Recruiter)"),
            Application(user_id=1, job_id=3, status="applied",
                        applied_date="Mar 20, 2026", contact="James T. (Hiring Manager)"),
            Application(user_id=1, job_id=4, status="applied",
                        applied_date="Mar 22, 2026"),
            Application(user_id=1, job_id=2, status="offer",
                        applied_date="Mar 10, 2026", contact="Maya R. (VP Eng)"),
            Application(user_id=1, job_id=5, status="rejected",
                        applied_date="Mar 5, 2026"),
        ]
        db.session.add_all(sample_apps)
        db.session.commit()
        print(f"[JobFindr] Seeded {len(raw_users)} users + sample applications into SQLite.")

    # ── Seed Recruiter account (separate from candidate users) ───────────
    if not User.query.filter_by(email="recruiter@jobfindr.ai").first():
        recruiter = User(
            id=100,
            name="Sarah Lin",
            email="recruiter@jobfindr.ai",
            password_hash=generate_password_hash("recruit123"),
            title="Senior Technical Recruiter",
            bio="Connecting world-class engineers with the best AI and ML teams.",
            location="San Francisco, CA",
            experience_years=8,
            is_recruiter=True,
            avatar="",
        )
        recruiter.skills = ["Talent Acquisition", "Technical Recruiting", "AI/ML Hiring"]
        recruiter.applications = []
        recruiter.saved_jobs = []
        db.session.add(recruiter)
        db.session.commit()
        print("[JobFindr] Seeded recruiter account: recruiter@jobfindr.ai / recruit123")
