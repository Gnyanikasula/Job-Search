"""
scheduler.py
Core pipeline — called by APScheduler nightly AND by POST /search/sync.
Phase 2: adds JD fetching before scoring.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Conservative scoring limit per run.
# Free tier is typically 20 req/day; 1 used by NL parser → 19 left.
# We cap at 15 to leave a buffer for tomorrow's NL parse + re-runs.
_MAX_SCORE_PER_RUN = 15


def default_terms(country: str) -> list[str]:
    if country == "India":
        return ["legal associate", "litigation associate", "corporate lawyer"]
    return ["data scientist", "machine learning engineer", "AI engineer"]


def run_daily_search(profile_id: str, trigger: str = "scheduled") -> dict:
    from backend.database import db
    from backend.ai.nl_parser import get_search_filters
    from backend.ai.scorer import score_job
    from backend.ai.jd_fetcher import fetch_jds_batch
    from backend.ai.gemini_client import quota_exhausted, reset_model_cache
    from backend.scrapers.jobspy_scraper import run_uk_search, run_india_search
    from backend.scrapers import safe_scrape, run_yc_jobs

    logger.info(f"=== Search started | profile={profile_id} | trigger={trigger} ===")

    summary = {
        "profile_id": profile_id, "trigger": trigger,
        "ran_at": datetime.utcnow().isoformat(),
        "jobs_fetched": 0, "jobs_new": 0, "jobs_scored": 0,
        "search_terms": [], "location": "", "error": "",
    }

    try:
        profile = db.get_profile(profile_id)
        if not profile:
            summary["error"] = "Profile not found"
            db.log_search(profile_id, trigger, 0, 0, summary["error"])
            return summary

        keys       = db.get_keys(profile_id)
        gemini_key = keys.get("gemini_key", "")
        cv_text    = profile.get("cv_text", "")
        description= profile.get("description", "")
        country    = profile.get("country", "UK")

        # Reset daily quota flag at start of each run (new day may have started)
        if gemini_key:
            reset_model_cache()

        # ── Step 2: parse description ────────────────────────────────────────
        filters      = get_search_filters(description, gemini_key)
        search_terms = filters.get("search_terms") or default_terms(country)
        location     = (filters.get("location")
                        or profile.get("location")
                        or ("India" if country == "India" else "London, UK"))
        summary["search_terms"] = search_terms
        summary["location"]     = location
        logger.info(f"Search terms: {search_terms} | Location: {location}")

        # ── Step 3: scrape ───────────────────────────────────────────────────
        raw_jobs: list[dict] = []
        search_fn = run_india_search if country == "India" else run_uk_search
        for term in search_terms[:3]:
            raw_jobs += safe_scrape(
                lambda t=term: search_fn(t, location), f"JobSpy[{term}]"
            )
        if country == "UK":
            raw_jobs += safe_scrape(
                lambda: run_yc_jobs(search_terms[0] if search_terms else ""),
                "YC Jobs"
            )
        summary["jobs_fetched"] = len(raw_jobs)
        logger.info(f"Total raw jobs fetched: {len(raw_jobs)}")

        # ── Step 4: dedupe + store ───────────────────────────────────────────
        jobs_new = 0
        for job in raw_jobs:
            if not job.get("title"):
                continue
            if db.upsert_job(profile_id, job):
                jobs_new += 1
        summary["jobs_new"] = jobs_new
        logger.info(f"New jobs stored: {jobs_new}")

        # ── Step 5 (Phase 2): fetch full JDs for unscored new jobs ──────────
        if jobs_new > 0:
            unscored = [j for j in db.get_jobs(profile_id, status="New", limit=_MAX_SCORE_PER_RUN)
                        if j.get("score", -1) == -1]
            if unscored:
                logger.info(f"Fetching full JDs for {len(unscored)} jobs…")
                unscored = fetch_jds_batch(unscored, max_jobs=_MAX_SCORE_PER_RUN)
                # Persist enriched descriptions back to DB
                for job in unscored:
                    if job.get("description"):
                        db.update_job_description(job["id"], job["description"])

        # ── Step 6: score ────────────────────────────────────────────────────
        scored = 0
        if gemini_key and cv_text and cv_text.strip():
            if quota_exhausted():
                logger.info("Daily Gemini quota already exhausted — skipping scoring.")
            else:
                to_score = [j for j in db.get_jobs(profile_id, status="New",
                                                     limit=_MAX_SCORE_PER_RUN)
                            if j.get("score", -1) == -1]
                logger.info(f"Scoring {len(to_score)} jobs (cap={_MAX_SCORE_PER_RUN})…")
                for job in to_score:
                    if quota_exhausted():
                        logger.info("Daily quota hit during scoring — stopping.")
                        break
                    result = score_job(job, cv_text, profile_id, gemini_key, db)
                    db.update_job_score(job["id"], result.get("score", -1), result)
                    scored += 1

        summary["jobs_scored"] = scored

        # ── Step 7: log ──────────────────────────────────────────────────────
        db.log_search(profile_id, trigger, len(raw_jobs), jobs_new)
        logger.info(f"=== Search done | {summary} ===")
        return summary

    except Exception as e:
        logger.exception(f"Pipeline crashed: {e}")
        summary["error"] = str(e)
        try:
            db.log_search(profile_id, trigger,
                          summary["jobs_fetched"], summary["jobs_new"], str(e))
        except Exception:
            pass
        return summary


def build_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(run_daily_search, "cron", hour=6, minute=0,
                      args=["gnyani"], id="daily_gnyani", replace_existing=True)
    scheduler.add_job(run_daily_search, "cron", hour=6, minute=0,
                      args=["friend"], id="daily_friend", replace_existing=True)
    return scheduler
