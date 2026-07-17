"""
scrapers/jobspy_scraper.py
Wraps the python-jobspy library. Returns a list of normalised job dicts.
Never raises — a failure of any single site returns [] for that site.
"""
import logging

logger = logging.getLogger(__name__)


def _safe_str(v) -> str:
    if v is None:
        return ""
    s = str(v)
    return "" if s.lower() == "nan" else s


def _normalise(row) -> dict:
    return {
        "title":       _safe_str(row.get("title")),
        "company":     _safe_str(row.get("company")),
        "location":    _safe_str(row.get("location")),
        "source":      _safe_str(row.get("site")),
        "job_url":     _safe_str(row.get("job_url")),
        "description": _safe_str(row.get("description"))[:3000],
        "date_posted": _safe_str(row.get("date_posted")),
    }


def run_jobspy(search_term, location, country="UK",
               results_wanted=20, sites=None, hours_old=72) -> list[dict]:
    """
    Run JobSpy for ONE search term across the given sites.
    Each site is attempted independently; a site failure does not stop others.
    """
    try:
        from jobspy import scrape_jobs
    except ImportError:
        logger.error("python-jobspy not installed. Run: pip install python-jobspy")
        return []

    if sites is None:
        sites = ["indeed", "linkedin"]

    country_indeed = "UK" if country == "UK" else "India"

    all_jobs: list[dict] = []
    for site in sites:
        try:
            logger.info(f"JobSpy → {site} | '{search_term}' | {location}")
            df = scrape_jobs(
                site_name=[site],
                search_term=search_term,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                country_indeed=country_indeed,
                linkedin_fetch_description=False,
                verbose=0,
            )
            if df is not None and not df.empty:
                jobs = [_normalise(row) for _, row in df.iterrows()]
                logger.info(f"  {site}: {len(jobs)} jobs")
                all_jobs.extend(jobs)
            else:
                logger.info(f"  {site}: 0 jobs")
        except Exception as e:
            logger.warning(f"  {site} failed: {e}")
            continue

    return all_jobs


def run_uk_search(search_term, location="London, UK") -> list[dict]:
    return run_jobspy(search_term, location, country="UK")


def run_india_search(search_term, location="India") -> list[dict]:
    return run_jobspy(search_term, location, country="India")
