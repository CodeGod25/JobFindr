"""Recommendations routes + REST API — supports algo toggle."""

import re
from typing import Optional
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from ..models import User
from ..ml.preprocessor import build_user_profile_text

recs_bp = Blueprint("recommendations", __name__)


def _current_user() -> Optional[User]:
    uid = session.get("user_id")
    if uid is None:
        return None
    return User.query.get(uid)


@recs_bp.route("/recommendations")
def recommendations():
    user = _current_user()
    if not user:
        return redirect(url_for("auth.login"))

    algo = request.args.get("algo", "tfidf")
    if algo not in ("tfidf", "keyword", "hybrid"):
        algo = "tfidf"

    rec = current_app.recommender
    jobs = rec.recommend_for_user(user.to_dict(), top_n=12, algo=algo)

    algo_labels = {
        "tfidf":   ("TF-IDF Neural", "psychology"),
        "keyword": ("Keyword Match", "tag"),
        "hybrid":  ("Hybrid",        "science"),
    }
    label, icon = algo_labels[algo]

    return render_template(
        "recommendations.html",
        user=user.to_dict(),
        jobs=jobs,
        algo=algo,
        algo_label=label,
        algo_icon=icon,
    )


@recs_bp.route("/api/recommend", methods=["POST"])
def api_recommend():
    """
    REST endpoint for ML recommendations.
    Accepts JSON: { "skills": "Python ML NLP...", "algo": "tfidf|keyword|hybrid", "top_n": 10 }
    """
    data = request.get_json(force=True, silent=True) or {}
    skills_text = data.get("skills", "")
    algo = data.get("algo", "tfidf")
    if algo not in ("tfidf", "keyword", "hybrid"):
        algo = "tfidf"

    if not skills_text.strip():
        user = _current_user()
        if user:
            skills_text = build_user_profile_text(user.to_dict())
        else:
            return jsonify({"error": "No skills provided and no logged-in user"}), 400

    top_n = int(data.get("top_n", 10))
    rec = current_app.recommender
    jobs = rec.recommend(skills_text, top_n=top_n, algo=algo)

    clean_jobs = []
    for j in jobs:
        cj = dict(j)
        cj["match_reason"] = re.sub(r"<[^>]+>", "", cj.get("match_reason", ""))
        clean_jobs.append(cj)

    return jsonify({"count": len(clean_jobs), "algo": algo, "results": clean_jobs})
