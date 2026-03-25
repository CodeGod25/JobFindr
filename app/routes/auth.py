"""Auth routes: login, register, logout — using SQLAlchemy + password hashing."""

from typing import Optional
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
from ..models import db, User

auth_bp = Blueprint("auth", __name__)


def _find_user(email: str) -> Optional[User]:
    return User.query.filter_by(email=email).first()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = _find_user(email)
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_title"] = user.title
            session["user_avatar"] = user.avatar or ""
            session["is_recruiter"] = user.is_recruiter
            return redirect(url_for("jobs.feed"))
        error = "Invalid email or password. Try: alex@jobfindr.ai / password123"
    return render_template("auth.html", mode="login", error=error)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        title = request.form.get("title", "").strip()

        if User.query.filter_by(email=email).first():
            error = "An account with that email already exists."
            return render_template("auth.html", mode="register", error=error)

        user = User(
            name=name or "New User",
            email=email,
            password_hash=generate_password_hash(password),
            title=title or "Professional",
        )
        user.skills = []
        user.applications = []
        user.saved_jobs = []
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session["user_name"] = user.name
        session["user_title"] = user.title
        session["user_avatar"] = ""
        session["is_recruiter"] = False
        return redirect(url_for("jobs.feed"))
    return render_template("auth.html", mode="register", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
