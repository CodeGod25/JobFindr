"""Flask application factory for JobFindr."""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .models import db
from .routes.auth import auth_bp
from .routes.jobs import jobs_bp
from .routes.profile import profile_bp
from .routes.applications import apps_bp
from .routes.recommendations import recs_bp
from .routes.recruiter import recruiter_bp
from .routes.oauth import oauth_bp, init_oauth


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
    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(apps_bp, url_prefix="/applications")
    app.register_blueprint(recs_bp, url_prefix="/recommendations")
    app.register_blueprint(recruiter_bp, url_prefix="/recruiter")
    app.register_blueprint(oauth_bp, url_prefix="/oauth")
    
    # Create database tables (skip if in serverless environment)
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:
        print(f"Warning: Could not create database tables: {e}")
        print("Running in serverless environment - using in-memory database fallback")
    
    return app
