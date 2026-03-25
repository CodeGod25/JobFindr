"""Jobs routes: landing, feed (with search), job detail, dashboard."""

from typing import Optional
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from ..models import User

jobs_bp = Blueprint("jobs", __name__)


def _current_user() -> Optional[User]:
    uid = session.get("user_id")
    if uid is None:
        return None
    return User.query.get(uid)


@jobs_bp.route("/")
def landing():
    return render_template("landing.html")


@jobs_bp.route("/jobs")
def feed():
    user = _current_user()
    if not user:
        return redirect(url_for("auth.login"))

    rec = current_app.recommender
    filter_type = request.args.get("filter", "for_you")
    search_q = request.args.get("q", "").strip()
    user_dict = user.to_dict()

    # ── Search mode ──────────────────────────────────────────────────────
    if search_q:
        jobs = rec.recommend(search_q, top_n=12, algo="tfidf")
    # ── Remote filter ────────────────────────────────────────────────────
    elif filter_type == "remote":
        all_jobs = rec.all_jobs()
        scored = rec.recommend_for_user(user_dict, top_n=50)
        scored_map = {j["id"]: j for j in scored}
        jobs = [scored_map[j["id"]] for j in all_jobs
                if "Remote" in j.get("type", "") and j["id"] in scored_map]
    # ── Senior filter ────────────────────────────────────────────────────
    elif filter_type == "senior":
        scored = rec.recommend_for_user(user_dict, top_n=15)
        jobs = [j for j in scored
                if "Senior" in j.get("title", "") or "Staff" in j.get("title", "")]
    # ── Default: AI personalised ─────────────────────────────────────────
    else:
        jobs = rec.recommend_for_user(user_dict, top_n=10)

    return render_template(
        "feed.html",
        jobs=jobs,
        user=user_dict,
        active_filter=filter_type,
        search_q=search_q,
    )


@jobs_bp.route("/jobs/<int:job_id>")
def job_detail(job_id: int):
    user = _current_user()
    if not user:
        return redirect(url_for("auth.login"))

    rec = current_app.recommender
    job = rec.get_job_by_id(job_id)
    if not job:
        return "Job not found", 404

    user_dict = user.to_dict()
    from ..ml.preprocessor import build_user_profile_text
    query = build_user_profile_text(user_dict)
    all_recs = rec.recommend(query, top_n=50)
    matched = next((j for j in all_recs if j["id"] == job_id), None)
    if matched:
        job.update({
            "match_score": matched["match_score"],
            "match_reason": matched["match_reason"],
            "svg_offset": matched["svg_offset"],
            "salary_display": matched["salary_display"],
        })
    else:
        job["match_score"] = 60
        job["match_reason"] = "This role matches your general professional profile."
        job["svg_offset"] = 70.4
        job["salary_display"] = rec._format_salary(
            job.get("salary_min", 0), job.get("salary_max", 0))

    # Score breakdown for radar chart
    breakdown = rec.get_score_breakdown(user_dict, job)

    # Similar jobs
    similar = [j for j in rec.recommend_for_user(user_dict, top_n=5)
               if j["id"] != job_id][:3]

    return render_template(
        "job_detail.html",
        job=job,
        user=user_dict,
        similar_jobs=similar,
        breakdown=breakdown,
    )


@jobs_bp.route("/dashboard")
def dashboard():
    user = _current_user()
    if not user:
        return redirect(url_for("auth.login"))
    rec = current_app.recommender
    top_jobs = rec.recommend_for_user(user.to_dict(), top_n=5)
    return render_template("candidate_dashboard.html", user=user.to_dict(), top_jobs=top_jobs)


@jobs_bp.route("/career")
def career():
    user = _current_user()
    return render_template("career.html", user=user.to_dict() if user else None)
