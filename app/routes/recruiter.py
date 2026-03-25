"""Recruiter portal and company profile routes — uses SQLAlchemy."""

from typing import Optional
from flask import Blueprint, render_template, session, redirect, url_for, current_app
from ..models import User

recruiter_bp = Blueprint("recruiter", __name__)

# Static company profiles for demo
COMPANIES = {
    1: {
        "id": 1,
        "name": "Stripe",
        "tagline": "Economic infrastructure for the internet",
        "industry": "Fintech / Payments",
        "size": "4,000+ employees",
        "founded": 2010,
        "location": "San Francisco, CA",
        "website": "https://stripe.com",
        "description": "Stripe builds economic infrastructure for the internet. Businesses of every size—from new startups to public companies—use our software to accept payments and manage their businesses online.",
        "culture": ["Move fast, safely", "Build for the long term", "Global inclusivity"],
        "perks": ["Competitive equity", "Remote-friendly", "Annual team offsites", "Learning stipend"],
        "open_roles": [1, 6],
    },
    2: {
        "id": 2,
        "name": "OpenAI",
        "tagline": "Ensuring artificial general intelligence benefits all of humanity",
        "industry": "AI Research",
        "size": "700+ employees",
        "founded": 2015,
        "location": "San Francisco, CA",
        "website": "https://openai.com",
        "description": "OpenAI is an AI research and deployment company. Our mission is to ensure that artificial general intelligence benefits all of humanity.",
        "culture": ["Curiosity driven", "Long-term thinking", "Responsible AI"],
        "perks": ["Top-tier compensation", "Healthcare", "GPU compute access", "Conference travel"],
        "open_roles": [4],
    },
}


def _current_user() -> Optional[User]:
    uid = session.get("user_id")
    if uid is None:
        return None
    return User.query.get(uid)


@recruiter_bp.route("/recruiter")
def recruiter_portal():
    user = _current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if not user.is_recruiter:
        return redirect(url_for("jobs.feed"))

    all_jobs = current_app.recommender.all_jobs()
    return render_template("recruiter.html", user=user.to_dict(), jobs=all_jobs[:8])


@recruiter_bp.route("/company/<int:company_id>")
def company_profile(company_id: int):
    company = COMPANIES.get(company_id)
    if not company:
        return "Company not found", 404

    rec = current_app.recommender
    open_jobs = [rec.get_job_by_id(jid) for jid in company.get("open_roles", [])]
    open_jobs = [j for j in open_jobs if j is not None]
    for job in open_jobs:
        job["salary_display"] = rec._format_salary(
            job.get("salary_min", 0), job.get("salary_max", 0))

    user = _current_user()
    return render_template(
        "company_profile.html",
        company=company,
        jobs=open_jobs,
        user=user.to_dict() if user else None,
    )
