"""Applications tracker routes — reads from SQLAlchemy DB."""

from flask import Blueprint, render_template, session, redirect, url_for
from ..models import User, Job, Application

apps_bp = Blueprint("applications", __name__)

PIPELINE_STAGES = [
    {"key": "applied",   "label": "Applied",    "icon": "send",           "color": "text-blue-400",    "bg": "bg-blue-400/10"},
    {"key": "interview", "label": "Interviews", "icon": "groups",         "color": "text-amber-400",   "bg": "bg-amber-400/10"},
    {"key": "offer",     "label": "Offers",     "icon": "celebration",    "color": "text-emerald-400", "bg": "bg-emerald-400/10"},
    {"key": "rejected",  "label": "Archived",   "icon": "do_not_disturb", "color": "text-red-400",     "bg": "bg-red-400/10"},
]


@apps_bp.route("/applications")
def applications():
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("auth.login"))

    user = User.query.get(uid)
    if not user:
        return redirect(url_for("auth.login"))

    # Fetch all applications for this user with job data
    db_apps = (
        Application.query
        .filter_by(user_id=uid)
        .join(Job, Application.job_id == Job.id)
        .all()
    )

    app_list = []
    for app in db_apps:
        j = app.job
        app_list.append({
            "id": app.id,
            "job_id": app.job_id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "status": app.status,
            "applied_date": app.applied_date or "—",
            "salary_display": _fmt_salary(j.salary_min, j.salary_max),
            "contact": app.contact or None,
        })

    pipeline = {}
    for stage in PIPELINE_STAGES:
        pipeline[stage["key"]] = [a for a in app_list if a["status"] == stage["key"]]

    return render_template(
        "applications.html",
        user=user.to_dict(),
        pipeline=pipeline,
        stages=PIPELINE_STAGES,
        total=len(app_list),
    )


def _fmt_salary(lo, hi):
    def f(v):
        return f"${v // 1000}k" if v >= 1000 else f"${v}"
    if lo and hi:
        return f"{f(lo)} – {f(hi)}"
    return "Competitive"
