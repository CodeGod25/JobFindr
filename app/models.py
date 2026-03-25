"""
SQLAlchemy models for JobFindr.
"""

import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    title = db.Column(db.String(120), default="")
    bio = db.Column(db.Text, default="")
    location = db.Column(db.String(120), default="")
    experience_years = db.Column(db.Integer, default=0)
    is_recruiter = db.Column(db.Boolean, default=False)
    avatar = db.Column(db.Text, default="")
    _skills = db.Column("skills", db.Text, default="[]")
    _applications = db.Column("applications", db.Text, default="[]")
    _saved_jobs = db.Column("saved_jobs", db.Text, default="[]")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # JSON helpers
    @property
    def skills(self):
        return json.loads(self._skills or "[]")

    @skills.setter
    def skills(self, value):
        self._skills = json.dumps(value)

    @property
    def applications(self):
        return json.loads(self._applications or "[]")

    @applications.setter
    def applications(self, value):
        self._applications = json.dumps(value)

    @property
    def saved_jobs(self):
        return json.loads(self._saved_jobs or "[]")

    @saved_jobs.setter
    def saved_jobs(self, value):
        self._saved_jobs = json.dumps(value)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "title": self.title,
            "bio": self.bio,
            "location": self.location,
            "experience_years": self.experience_years,
            "is_recruiter": self.is_recruiter,
            "avatar": self.avatar,
            "skills": self.skills,
            "applications": self.applications,
            "saved_jobs": self.saved_jobs,
        }


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), default="")
    type = db.Column(db.String(50), default="Full-time")
    dept = db.Column(db.String(100), default="Engineering")
    salary_min = db.Column(db.Integer, default=0)
    salary_max = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, default="")
    posted_at = db.Column(db.String(50), default="")
    source = db.Column(db.String(50), default="local")
    _skills = db.Column("skills", db.Text, default="[]")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def skills(self):
        return json.loads(self._skills or "[]")

    @skills.setter
    def skills(self, value):
        self._skills = json.dumps(value)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "type": self.type,
            "dept": self.dept,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "description": self.description,
            "posted_at": self.posted_at,
            "skills": self.skills,
            "source": self.source,
        }


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    status = db.Column(db.String(50), default="applied")
    applied_date = db.Column(db.String(50), default="")
    contact = db.Column(db.String(200), default="")
    notes = db.Column(db.Text, default="")

    user = db.relationship("User", backref="db_applications")
    job = db.relationship("Job", backref="job_applications")


class SavedJob(db.Model):
    __tablename__ = "saved_jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
