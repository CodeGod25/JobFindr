"""
JobFindr ML Recommendation Engine — Phase 2.

Three recommendation strategies:
  - TF-IDF cosine similarity  (default, most semantic)
  - Keyword overlap / Jaccard  (simple, transparent)
  - Hybrid (0.7 × TF-IDF + 0.3 × Keyword)

Also provides get_score_breakdown() for the radar chart.
"""

import json
import os
import re
from typing import Optional, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from .preprocessor import build_job_corpus, build_user_profile_text, build_query_from_skills

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Dept demand scores (static, illustrative)
DEPT_DEMAND = {
    "AI Research":      95,
    "Machine Learning": 92,
    "Data Science":     88,
    "MLOps":            85,
    "Platform":         80,
    "Backend":          78,
    "Full-Stack":       75,
    "Design":           70,
    "Product":          72,
    "Frontend":         74,
}


class JobRecommender:
    """
    Content-based job recommendation engine.

    Supports three algorithms:
      tfidf    — TF-IDF cosine similarity (semantic)
      keyword  — Jaccard token overlap
      hybrid   — 0.7 × tfidf + 0.3 × keyword
    """

    def __init__(self):
        self.jobs: List[dict] = []
        self.corpus: List[str] = []
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=8000,
            sublinear_tf=True,
        )
        self.tfidf_matrix = None
        self._load_and_build()

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def _load_and_build(self):
        """Load jobs from DB first, fallback to jobs.json."""
        print("Initializing JobRecommender index...")
        try:
            from ..models import Job
            db_jobs = Job.query.all()
            if db_jobs:
                self.jobs = [j.to_dict() for j in db_jobs]
                print(f"Loaded {len(self.jobs)} jobs from database.")
            else:
                print("Database empty, falling back to JSON.")
                self._load_from_json()
        except Exception as e:
            print(f"Database access failed during recommender init: {e}. Falling back to JSON.")
            self._load_from_json()

        if not self.jobs:
            print("Warning: No jobs found in database or JSON. Recommender will be empty.")
            self.corpus = []
            self.tfidf_matrix = None
            return

        self.corpus = [build_job_corpus(job) for job in self.jobs]
        
        # Ensure we have at least one valid document for TF-IDF
        valid_corpus = [c for c in self.corpus if c.strip()]
        if valid_corpus:
            try:
                self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
                print("TF-IDF matrix built successfully.")
            except Exception as e:
                print(f"Error building TF-IDF matrix: {e}")
                self.tfidf_matrix = None
        else:
            print("Warning: All job corpora are empty. TF-IDF matching disabled.")
            self.tfidf_matrix = None

    def _load_from_json(self):
        jobs_path = os.path.join(DATA_DIR, "jobs.json")
        with open(jobs_path, encoding="utf-8") as f:
            self.jobs = json.load(f)

    def reload(self):
        """Re-fit the TF-IDF index (call after adding new jobs)."""
        self._load_and_build()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recommend(self, query_text: str, top_n: int = 10,
                  algo: str = "tfidf") -> List[dict]:
        """
        Rank jobs for a free-text query using the selected algorithm.

        Args:
            query_text: user profile or skills string
            top_n:      max results
            algo:       "tfidf" | "keyword" | "hybrid"
        """
        if algo == "keyword":
            return self._recommend_keyword(query_text, top_n)
        elif algo == "hybrid":
            return self._recommend_hybrid(query_text, top_n)
        return self._recommend_tfidf(query_text, top_n)

    def recommend_for_user(self, user: dict, top_n: int = 10,
                           algo: str = "tfidf") -> List[dict]:
        """Convenience wrapper — builds query from a user profile dict."""
        query = build_user_profile_text(user)
        return self.recommend(query, top_n=top_n, algo=algo)

    def get_job_by_id(self, job_id: int) -> Optional[dict]:
        for job in self.jobs:
            if job["id"] == job_id:
                return dict(job)
        return None

    def all_jobs(self) -> List[dict]:
        jobs = []
        for job in self.jobs:
            j = dict(job)
            j["salary_display"] = self._format_salary(
                j.get("salary_min", 0), j.get("salary_max", 0)
            )
            jobs.append(j)
        return jobs

    def get_score_breakdown(self, user: dict, job: dict) -> dict:
        """
        Return a 5-axis score breakdown dict (0-100) for the radar chart.

        Axes:
          skills_match   — % of job skills found in user skills (exact + partial)
          role_alignment — TF-IDF cosine similarity × 100 for this pair
          salary_fit     — how well salary range overlaps user expectations
          seniority      — years experience vs inferred role seniority
          demand_score   — dept demand (static market signal)
        """
        query = build_user_profile_text(user)
        user_skills = {s.lower() for s in user.get("skills", [])}
        job_skills = [s.lower() for s in job.get("skills", [])]
        yoe = user.get("experience_years", 3)

        # 1. Skills Match (0-100)
        if job_skills:
            matched = sum(
                1 for s in job_skills
                if any(u in s or s in u for u in user_skills)
            )
            skills_match = min(100, int(matched / len(job_skills) * 100))
        else:
            skills_match = 50

        # 2. Role Alignment — TF-IDF cosine for this specific pair
        if self.tfidf_matrix is not None:
            clean_q = build_query_from_skills(query)
            q_vec = self.vectorizer.transform([clean_q])
            idx = next(
                (i for i, j in enumerate(self.jobs) if j["id"] == job["id"]),
                None
            )
            if idx is not None:
                sim = float(cosine_similarity(
                    q_vec, self.tfidf_matrix[idx]
                ).flatten()[0])
                role_alignment = min(99, max(40, int(sim * 220)))
            else:
                role_alignment = 60
        else:
            role_alignment = 60

        # 3. Salary Fit (0-100) — how well midpoint compares to $150k baseline
        sal_mid = (job.get("salary_min", 0) + job.get("salary_max", 0)) / 2
        salary_fit = min(100, max(20, int((sal_mid / 200_000) * 100)))

        # 4. Seniority Match (0-100) — based on title keywords vs yoe
        title_lower = job.get("title", "").lower()
        if "senior" in title_lower or "staff" in title_lower or "lead" in title_lower:
            required_yoe = 6
        elif "principal" in title_lower or "director" in title_lower:
            required_yoe = 9
        elif "junior" in title_lower or "associate" in title_lower:
            required_yoe = 1
        else:
            required_yoe = 3
        seniority = min(100, max(20, int(100 - abs(yoe - required_yoe) * 12)))

        # 5. Demand Score — static from dept map
        dept = job.get("dept", "")
        demand_score = DEPT_DEMAND.get(dept, 70)

        return {
            "skills_match": skills_match,
            "role_alignment": role_alignment,
            "salary_fit": salary_fit,
            "seniority": seniority,
            "demand_score": demand_score,
        }

    # ------------------------------------------------------------------
    # Algorithm implementations
    # ------------------------------------------------------------------

    def _recommend_tfidf(self, query_text: str, top_n: int) -> List[dict]:
        """TF-IDF cosine similarity — most semantic."""
        clean_query = build_query_from_skills(query_text)
        query_vec = self.vectorizer.transform([clean_query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_n]

        results = []
        for rank, idx in enumerate(top_indices):
            job = dict(self.jobs[idx])
            raw = float(similarities[idx])
            score = int(min(99, max(40, round(raw * 200))))
            if rank == 0 and score < 85:
                score = min(99, score + 20)
            job["match_score"] = score
            job["algo_label"] = "TF-IDF Neural"
            job["match_reason"] = self._explain_match(query_text, job)
            job["svg_offset"] = self._score_to_svg_offset(score)
            job["salary_display"] = self._format_salary(
                job.get("salary_min", 0), job.get("salary_max", 0))
            results.append(job)
        return results

    def _recommend_keyword(self, query_text: str, top_n: int) -> List[dict]:
        """Jaccard keyword overlap — simple and transparent."""
        query_tokens = set(re.sub(r"[^a-z0-9 ]", " ",
                                  query_text.lower()).split())

        scored = []
        for job in self.jobs:
            job_tokens = set(" ".join(job.get("skills", [])).lower().split())
            job_tokens |= set(job.get("title", "").lower().split())
            union = query_tokens | job_tokens
            intersection = query_tokens & job_tokens
            jaccard = len(intersection) / len(union) if union else 0
            scored.append((jaccard, job))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for rank, (raw, job) in enumerate(scored[:top_n]):
            j = dict(job)
            score = int(min(99, max(35, round(raw * 300))))
            if rank == 0 and score < 80:
                score = min(99, score + 15)
            j["match_score"] = score
            j["algo_label"] = "Keyword Match"
            j["match_reason"] = self._explain_match(query_text, j)
            j["svg_offset"] = self._score_to_svg_offset(score)
            j["salary_display"] = self._format_salary(
                j.get("salary_min", 0), j.get("salary_max", 0))
            results.append(j)
        return results

    def _recommend_hybrid(self, query_text: str, top_n: int) -> List[dict]:
        """Hybrid: 0.7 × TF-IDF + 0.3 × Keyword."""
        tfidf_results = self._recommend_tfidf(query_text, top_n=len(self.jobs))
        keyword_results = self._recommend_keyword(query_text, top_n=len(self.jobs))

        tfidf_map = {j["id"]: j["match_score"] for j in tfidf_results}
        kw_map = {j["id"]: j["match_score"] for j in keyword_results}

        blended = []
        for job in self.jobs:
            tid = job["id"]
            t_score = tfidf_map.get(tid, 40)
            k_score = kw_map.get(tid, 35)
            hybrid_score = int(0.7 * t_score + 0.3 * k_score)
            blended.append((hybrid_score, job))

        blended.sort(key=lambda x: x[0], reverse=True)
        results = []
        for rank, (score, job) in enumerate(blended[:top_n]):
            j = dict(job)
            if rank == 0 and score < 85:
                score = min(99, score + 10)
            j["match_score"] = score
            j["algo_label"] = "Hybrid"
            j["match_reason"] = self._explain_match(query_text, j)
            j["svg_offset"] = self._score_to_svg_offset(score)
            j["salary_display"] = self._format_salary(
                j.get("salary_min", 0), j.get("salary_max", 0))
            results.append(j)
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _explain_match(self, query_text: str, job: dict) -> str:
        query_tokens = set(query_text.lower().split())
        job_skills = [s.lower() for s in job.get("skills", [])]
        matched = [s for s in job_skills
                   if any(tok in s or s in tok for tok in query_tokens)]
        if len(matched) >= 2:
            highlighted = matched[:3]
            skill_str = " and ".join(
                f'<span class="text-white font-semibold">{s.title()}</span>'
                for s in highlighted
            )
            return f"Your expertise in {skill_str} aligns strongly with this role's requirements."
        elif len(matched) == 1:
            s = matched[0]
            return (
                f'Your background in <span class="text-white font-semibold">{s.title()}</span> '
                f"is a key match for {job.get('company', 'this company')}."
            )
        else:
            top_skills = job.get("skills", [])[:2]
            if top_skills:
                skill_str = " and ".join(
                    f'<span class="text-white font-semibold">{s}</span>'
                    for s in top_skills
                )
                return f"This role values {skill_str} — skills in high demand in your career trajectory."
            return "This role closely aligns with your professional profile and experience level."

    def _score_to_svg_offset(self, score: int) -> float:
        circumference = 175.9
        return round(circumference * (1 - score / 100), 1)

    def _format_salary(self, salary_min: int, salary_max: int) -> str:
        def fmt(v):
            return f"${v // 1000}k" if v >= 1000 else f"${v}"
        if salary_min and salary_max:
            return f"{fmt(salary_min)} – {fmt(salary_max)}"
        elif salary_max:
            return f"Up to {fmt(salary_max)}"
        return "Competitive"
