"""
scrapers/__init__.py
Safe wrapper and YC Jobs scraper (public JSON, no Playwright needed).
"""
import logging
import requests

logger = logging.getLogger(__name__)

# A browser-like User-Agent — YC's endpoint returns 406 without one.
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
}


def safe_scrape(scraper_fn, source_name: str) -> list[dict]:
    """One failure must NEVER crash the pipeline. Returns [] on any exception."""
    try:
        results = scraper_fn()
        logger.info(f"{source_name}: {len(results)} jobs")
        return results
    except Exception as e:
        logger.warning(f"{source_name} failed: {e}")
        return []


def run_yc_jobs(search_term: str = "") -> list[dict]:
    """
    YC 'Work at a Startup' public feed. Requires a browser UA (else 406).
    Filters by search_term substring on role title. Best-effort only.
    """
    url = "https://www.workatastartup.com/companies/jobs.json"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.info(f"YC Jobs returned HTTP {resp.status_code} — skipping.")
            return []
        data = resp.json()
    except Exception as e:
        logger.info(f"YC Jobs unavailable: {e}")
        return []

    # The feed shape can vary; be defensive.
    items = data if isinstance(data, list) else data.get("jobs", [])
    jobs = []
    term = (search_term or "").lower()
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("role") or ""
        if term and term not in title.lower():
            continue
        company = item.get("company")
        if isinstance(company, dict):
            company = company.get("name", "")
        jobs.append({
            "title":       title,
            "company":     company or "",
            "location":    item.get("location", "Remote"),
            "source":      "YC Jobs",
            "job_url":     item.get("url", "https://www.workatastartup.com/jobs"),
            "description": (item.get("description") or "")[:3000],
            "date_posted": item.get("created_at", ""),
        })
    return jobs
