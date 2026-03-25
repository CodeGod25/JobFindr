"""User profile routes — reads/writes from SQLAlchemy DB."""

from typing import Optional
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, current_app, jsonify)
from werkzeug.utils import secure_filename
from ..models import db, User
from ..ml.resume_parser import parse_resume

profile_bp = Blueprint("profile", __name__)

ALLOWED_EXTENSIONS = {"pdf"}


def _current_user() -> Optional[User]:
    uid = session.get("user_id")
    if uid is None:
        return None
    return User.query.get(uid)


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@profile_bp.route("/profile")
def profile():
    user = _current_user()
    if not user:
        return redirect(url_for("auth.login"))
    return render_template("profile.html", user=user.to_dict())


@profile_bp.route("/profile/update", methods=["POST"])
def update_profile():
    user = _current_user()
    if not user:
        return redirect(url_for("auth.login"))

    skills_raw = request.form.get("skills", "")
    bio = request.form.get("bio", "")
    title = request.form.get("title", "")

    if skills_raw:
        user.skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    if bio:
        user.bio = bio
    if title:
        user.title = title
        session["user_title"] = title

    db.session.commit()

    try:
        current_app.recommender.reload()
    except Exception:
        pass

    return redirect(url_for("profile.profile"))


@profile_bp.route("/profile/parse-resume", methods=["POST"])
def parse_resume_route():
    """Accept a PDF upload, parse it and return a JSON breakdown."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["resume"]
    if not file or not file.filename or not _allowed(file.filename):
        return jsonify({"error": "Please upload a PDF file"}), 400

    pdf_bytes = file.read()
    result = parse_resume(pdf_bytes)

    if "error" in result:
        return jsonify(result), 422

    return jsonify(result)


@profile_bp.route("/profile/apply-resume-skills", methods=["POST"])
def apply_resume_skills():
    """Persist skills extracted from resume to the user's profile."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(force=True)
    skills = data.get("skills", [])
    if not skills:
        return jsonify({"error": "No skills provided"}), 400

    user.skills = [s.strip() for s in skills if s.strip()]
    db.session.commit()
    try:
        current_app.recommender.reload()
    except Exception:
        pass

    return jsonify({"ok": True, "skill_count": len(user.skills)})
