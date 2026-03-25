"""Flask application factory for JobFindr."""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .models import db
from .routes.auth import auth_bp
from .routes.jobs import jobs_bp
from .routes.profile import profile_bp
from .routes.applications import apps_bp
from .routes.recommendations import recs_bp
from .routes.recruiter import recruiter_bp
from .routes.oauth import oauth_bp


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    
    # Configuration
    app.config["SECRET_KEY"] = "dev-secret-key"  # Change in production
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///jobfindr.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(apps_bp, url_prefix="/applications")
    app.register_blueprint(recs_bp, url_prefix="/recommendations")
    app.register_blueprint(recruiter_bp, url_prefix="/recruiter")
    app.register_blueprint(oauth_bp, url_prefix="/oauth")
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
