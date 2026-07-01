"""
ai/scorer.py
Scores a job against the user's CV using the shared Gemini client.
Caches results in SQLite (7-day cache). Never raises.
"""
import json
import logging
import re

from backend.ai.gemini_client import generate

logger = logging.getLogger(__name__)

EMPTY_SCORE = {
    "score": -1,
    "matched_skills": [],
    "missing_skills": [],
    "experience_gap": "",
    "red_flags": [],
    "verdict": "Not scored",
    "cover_letter_focus": "",
}


def _strip_json_fence(text: str) -> str:
    text = re.sub(r"^```json\s*", "", text.strip())
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def score_with_gemini(cv_text: str, job: dict, gemini_key: str) -> dict:
    jd_snippet = (job.get("description") or "")[:2000]
    prompt = f"""
You are a career coach scoring job-CV fit. Score this job for the candidate.

CV (truncated):
{cv_text[:2000]}

Job: {job.get('title')} at {job.get('company')} ({job.get('location')})
Job Description:
{jd_snippet}

Return ONLY a JSON object with:
- score: integer 0-100 (100 = perfect match)
- matched_skills: list of skills from CV that appear in JD
- missing_skills: list of skills in JD missing from CV
- experience_gap: short string describing experience mismatch (or "" if none)
- red_flags: list of concerns (over-qualified, requires visa, etc.)
- verdict: one-line summary of fit
- cover_letter_focus: what to emphasise in a cover letter

Return only valid JSON, no markdown, no explanation.
"""
    text = generate(gemini_key, prompt)
    if not text:
        return {**EMPTY_SCORE, "verdict": "Scoring unavailable (quota or key issue)"}
    try:
        result = json.loads(_strip_json_fence(text))
        # ensure score is an int
        result["score"] = int(result.get("score", -1))
        return {**EMPTY_SCORE, **result}
    except Exception as e:
        logger.warning(f"Could not parse score JSON for {job.get('title')}: {e}")
        return {**EMPTY_SCORE, "verdict": "Score parse failed"}


def score_job(job, cv_text, profile_id, gemini_key, db_module=None) -> dict:
    """Score a single job. Checks cache first. Returns score dict. Never raises."""
    if not cv_text or not cv_text.strip():
        return EMPTY_SCORE

    fingerprint = job.get("id", "")
    if not fingerprint and db_module:
        fingerprint = db_module.make_fingerprint(
            job.get("company", ""), job.get("title", ""), job.get("location", "")
        )

    if db_module and fingerprint:
        cached = db_module.get_cached_score(fingerprint, profile_id)
        if cached:
            logger.info(f"Score cache hit: {job.get('title')}")
            return cached["breakdown"]

    if not gemini_key:
        return {**EMPTY_SCORE, "verdict": "No Gemini key — scoring skipped"}

    result = score_with_gemini(cv_text, job, gemini_key)

    if db_module and fingerprint and result.get("score", -1) >= 0:
        db_module.cache_score(fingerprint, profile_id, result.get("score", -1), result)

    return result
