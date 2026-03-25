"""
Text preprocessing utilities for the JobFindr ML recommendation engine.
Cleans and normalises text before TF-IDF vectorisation.
"""

import re
import string

# Common English stop words (subset) — avoiding NLTK dependency
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "during",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "shall", "can", "need", "dare", "ought", "used", "as", "at", "this",
    "that", "these", "those", "it", "its", "we", "you", "they", "he", "she",
    "our", "your", "their", "my", "his", "her", "which", "who", "whom",
    "what", "when", "where", "why", "how", "all", "both", "each", "few",
    "more", "most", "other", "some", "such", "no", "not", "only", "same",
    "so", "than", "too", "very", "just", "over", "also", "i", "me", "us"
}


def clean_text(text: str) -> str:
    """
    Lowercase, remove punctuation and stop words from a text string.
    Returns a clean, space-separated token string.
    """
    if not isinstance(text, str):
        return ""
    # Lowercase
    text = text.lower()
    # Remove URLs
    text = re.sub(r"http\S+|www\S+", "", text)
    # Remove punctuation
    text = text.translate(str.maketrans("", "", string.punctuation))
    # Tokenise by whitespace
    tokens = text.split()
    # Remove stop words and short tokens
    tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]
    return " ".join(tokens)


def build_job_corpus(job: dict) -> str:
    """
    Convert a job listing dict into a single text string for vectorisation.
    Weights title and skills more heavily by repeating them.
    """
    title = job.get("title", "")
    company = job.get("company", "")
    description = job.get("description", "")
    skills = " ".join(job.get("skills", []))
    dept = job.get("dept", "")
    # Repeat title and skills 3× to boost their TF-IDF weight
    corpus = f"{title} {title} {title} {skills} {skills} {skills} {dept} {company} {description}"
    return clean_text(corpus)


def build_user_profile_text(user: dict) -> str:
    """
    Convert a user profile dict into a query text string for similarity search.
    """
    title = user.get("title", "")
    bio = user.get("bio", "")
    skills = " ".join(user.get("skills", []))
    # Repeat skills heavily as the primary signal
    profile = f"{title} {title} {skills} {skills} {skills} {bio}"
    return clean_text(profile)


def build_query_from_skills(skills_text: str) -> str:
    """
    Build a clean query string from a raw skills/description input string.
    Used for the /api/recommend endpoint.
    """
    return clean_text(skills_text)
