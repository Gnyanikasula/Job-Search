"""
ai/jd_fetcher.py  — Phase 2
Fetches the full job description from a job posting URL.
Uses requests + BeautifulSoup. Falls back gracefully on any failure.
Result is cached in the jobs.description column — never re-fetched.
"""
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}

# Selectors tried in order — first match wins
_JD_SELECTORS = [
    {"data-testid": "jobsearch-JobComponent-description"},  # Indeed
    {"class": re.compile(r"description|job-desc|jobDescription", re.I)},
    {"id": re.compile(r"description|job-desc|jobDescription", re.I)},
    "article",
    "main",
]

_MAX_CHARS = 4000
_REQUEST_TIMEOUT = 10


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # Remove noise
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "iframe", "noscript"]):
        tag.decompose()

    # Try targeted selectors first
    for sel in _JD_SELECTORS:
        if isinstance(sel, str):
            el = soup.find(sel)
        else:
            el = soup.find(attrs=sel)
        if el:
            text = el.get_text(separator=" ", strip=True)
            if len(text) > 200:
                return text[:_MAX_CHARS]

    # Fallback: body text
    body = soup.find("body")
    if body:
        return body.get_text(separator=" ", strip=True)[:_MAX_CHARS]

    return soup.get_text(separator=" ", strip=True)[:_MAX_CHARS]


def fetch_jd(url: str, existing_description: str = "") -> str:
    """
    Fetch full job description from URL.
    Returns the existing description unchanged if:
    - URL is empty or invalid
    - Existing description is already long enough (>500 chars)
    - Fetch fails for any reason
    """
    if not url or not url.startswith("http"):
        return existing_description

    # Already have a good description — don't re-fetch
    if existing_description and len(existing_description.strip()) > 500:
        return existing_description

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT,
                            allow_redirects=True)
        if resp.status_code != 200:
            logger.debug(f"JD fetch {resp.status_code} for {url[:60]}")
            return existing_description

        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type:
            return existing_description

        text = _extract_text(resp.text)
        if len(text) > 100:
            logger.debug(f"JD fetched: {len(text)} chars from {url[:60]}")
            return text

        return existing_description

    except Exception as e:
        logger.debug(f"JD fetch failed for {url[:60]}: {e}")
        return existing_description


def fetch_jds_batch(jobs: list[dict], max_jobs: int = 30,
                    delay: float = 0.5) -> list[dict]:
    """
    Fetch JDs for a batch of jobs. Modifies description in-place.
    Respects a small delay between requests to avoid hammering sites.
    Only fetches jobs that don't already have a long description.
    """
    to_fetch = [j for j in jobs
                if len((j.get("description") or "").strip()) < 500][:max_jobs]

    logger.info(f"JD fetcher: {len(to_fetch)} jobs need full descriptions")

    for i, job in enumerate(to_fetch):
        url = job.get("job_url") or job.get("url", "")
        job["description"] = fetch_jd(url, job.get("description", ""))
        if i < len(to_fetch) - 1:
            time.sleep(delay)

    return jobs
