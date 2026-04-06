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


def _seed_database():
    """Seed the database with demo users and jobs if empty."""
    if User.query.first():
        return  # Already seeded

    print("Seeding database with demo data...")
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    # 1. Seed Jobs
    jobs_path = os.path.join(data_dir, "jobs.json")
    if os.path.exists(jobs_path):
        with open(jobs_path, encoding="utf-8") as f:
            jobs_data = json.load(f)
            for j in jobs_data:
                db.session.add(Job(
                    title=j["title"],
                    company=j["company"],
                    location=j["location"],
                    type=j["type"],
                    dept=j["dept"],
                    salary_min=j["salary_min"],
                    salary_max=j["salary_max"],
                    description=j["description"],
                    posted_at=j["posted_at"],
                    skills=j["skills"],
                    source=j.get("source", "local")
                ))

    # 2. Seed Users
    users_path = os.path.join(data_dir, "users.json")
    if os.path.exists(users_path):
        with open(users_path, encoding="utf-8") as f:
            users_data = json.load(f)
            for u in users_data:
                db.session.add(User(
                    name=u["name"],
                    email=u["email"],
                    password_hash=generate_password_hash(u.get("password", "password123")),
                    title=u["title"],
                    bio=u["bio"],
                    location=u["location"],
                    experience_years=u["experience_years"],
                    avatar=u["avatar"],
                    skills=u["skills"],
                    is_recruiter=False
                ))

    # 3. Add explicit demo recruiter
    db.session.add(User(
        name="Sarah Lin",
        email="recruiter@jobfindr.ai",
        password_hash=generate_password_hash("recruit123"),
        title="Senior Talent Acquisition",
        bio="Recruiting the best engineering talent for JobFindr.",
        location="San Francisco, CA",
        experience_years=8,
        is_recruiter=True,
        skills=["Talent Acquisition", "Technical Recruiting", "HR Strategy"]
    ))

    db.session.commit()
    print("Database seeding completed.")
