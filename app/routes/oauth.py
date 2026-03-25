"""
OAuth 2.0 routes for Google and LinkedIn — powered by Authlib.

Required environment variables (set in .env):
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    LINKEDIN_CLIENT_ID
    LINKEDIN_CLIENT_SECRET

Callback URLs to register in your provider dashboards:
    Google  → http://127.0.0.1:5000/auth/google/callback
    LinkedIn→ http://127.0.0.1:5000/auth/linkedin/callback
"""
from __future__ import annotations
import os
from flask import Blueprint, redirect, url_for, session, request, current_app
from authlib.integrations.flask_client import OAuth
from ..models import db, User

oauth_bp = Blueprint("oauth", __name__)

# ── Authlib OAuth registry (initialised in create_app) ─────────────────────
oauth = OAuth()


def init_oauth(app):
    """Register Google and LinkedIn clients on the Authlib OAuth registry."""
    oauth.init_app(app)

    # ── Google ──────────────────────────────────────────────────────────────
    oauth.register(
        name="google",
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    # ── LinkedIn ─────────────────────────────────────────────────────────────
    # LinkedIn supports OpenID Connect (OIDC) since 2023 — scope: openid profile email
    oauth.register(
        name="linkedin",
        client_id=app.config.get("LINKEDIN_CLIENT_ID"),
        client_secret=app.config.get("LINKEDIN_CLIENT_SECRET"),
        # LinkedIn OIDC discovery document
        server_metadata_url="https://www.linkedin.com/oauth/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
    )


# ── Helpers ─────────────────────────────────────────────────────────────────

def _login_or_create(email: str, name: str, avatar: str = "") -> User:
    """Find existing user by email or create a new one. Returns the User."""
    user = User.query.filter_by(email=email).first()
    if not user:
        # Auto-register the OAuth user
        user = User(
            name=name or email.split("@")[0],
            email=email,
            password_hash="",          # no password for OAuth users
            title="",
            bio="",
            location="",
            experience_years=0,
            is_recruiter=False,
            avatar=avatar,
        )
        user.skills = []
        user.applications = []
        user.saved_jobs = []
        db.session.add(user)
        db.session.commit()
    return user


def _set_session(user: User):
    session["user_id"] = user.id
    session["user_name"] = user.name
    session["user_title"] = user.title
    session["user_avatar"] = user.avatar or ""
    session["is_recruiter"] = user.is_recruiter


# ── Google ──────────────────────────────────────────────────────────────────

@oauth_bp.route("/auth/google")
def google_login():
    redirect_uri = url_for("oauth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@oauth_bp.route("/auth/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo") or oauth.google.userinfo()
    email = userinfo.get("email", "")
    name = userinfo.get("name", "")
    avatar = userinfo.get("picture", "")

    if not email:
        return redirect(url_for("auth.login"))

    user = _login_or_create(email, name, avatar)
    _set_session(user)
    return redirect(url_for("jobs.feed"))


# ── LinkedIn ─────────────────────────────────────────────────────────────────

@oauth_bp.route("/auth/linkedin")
def linkedin_login():
    redirect_uri = url_for("oauth.linkedin_callback", _external=True)
    return oauth.linkedin.authorize_redirect(redirect_uri)


@oauth_bp.route("/auth/linkedin/callback")
def linkedin_callback():
    token = oauth.linkedin.authorize_access_token()
    userinfo = token.get("userinfo") or oauth.linkedin.userinfo()
    email = userinfo.get("email", "")
    name = userinfo.get("name", "")
    avatar = userinfo.get("picture", "")

    if not email:
        return redirect(url_for("auth.login"))

    user = _login_or_create(email, name, avatar)
    _set_session(user)
    return redirect(url_for("jobs.feed"))
