"""
scrapers/jobspy_scraper.py
Runs jobspy in an ISOLATED SUBPROCESS per site so a native crash (e.g. a broken
numpy build) can never take down the API server. Each site call has a timeout.
Never raises — any failure returns [] for that site.
"""
import sys
import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

MARKER = "###RESULT###"
PER_SITE_TIMEOUT = 90            # seconds; kill a hung/slow scrape
# Project root = three levels up from this file (backend/scrapers/this.py)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_one_site(site, search_term, location, country_indeed,
                  results_wanted=20, hours_old=72) -> list[dict]:
    """Invoke the isolated worker for a single site. Returns [] on any problem."""
    payload = json.dumps({
        "site": site,
        "search_term": search_term,
        "location": location,
        "results_wanted": results_wanted,
        "hours_old": hours_old,
        "country_indeed": country_indeed,
    })

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "backend.scrapers.scrape_worker"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=PER_SITE_TIMEOUT,
            cwd=str(_PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"  {site}: timed out after {PER_SITE_TIMEOUT}s")
        return []
    except Exception as e:
        logger.warning(f"  {site}: could not launch worker: {e}")
        return []

    # A native crash (segfault / broken numpy) => non-zero exit, no marker.
    if proc.returncode != 0 and MARKER not in (proc.stdout or ""):
        logger.warning(f"  {site}: worker crashed (exit {proc.returncode}). "
                       f"This is usually a broken numpy build — see README.")
        return []

    out = proc.stdout or ""
    if MARKER not in out:
        logger.warning(f"  {site}: no result marker in worker output")
        return []

    try:
        result = json.loads(out.split(MARKER, 1)[1].strip())
    except Exception as e:
        logger.warning(f"  {site}: could not parse worker output: {e}")
        return []

    if not result.get("ok"):
        logger.info(f"  {site}: {result.get('error', 'no jobs')}")
        return []

    jobs = result.get("jobs", [])
    logger.info(f"  {site}: {len(jobs)} jobs")
    return jobs


def run_jobspy(search_term, location, country="UK",
               results_wanted=20, sites=None, hours_old=72) -> list[dict]:
    """Run jobspy for ONE search term across sites, each in its own subprocess."""
    if sites is None:
        sites = ["indeed", "linkedin"]
    country_indeed = "India" if country == "India" else "UK"

    all_jobs: list[dict] = []
    for site in sites:
        logger.info(f"JobSpy → {site} | '{search_term}' | {location}")
        all_jobs += _run_one_site(site, search_term, location, country_indeed,
                                  results_wanted, hours_old)
    return all_jobs


def run_uk_search(search_term, location="London, UK") -> list[dict]:
    return run_jobspy(search_term, location, country="UK")


def run_india_search(search_term, location="India") -> list[dict]:
    return run_jobspy(search_term, location, country="India")
