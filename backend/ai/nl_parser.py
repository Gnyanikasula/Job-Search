"""
ai/nl_parser.py
Converts a user's natural-language job description into structured search filters.
Uses the shared Gemini client (auto-discovers model). Falls back to sensible
hardcoded defaults if the API is unavailable — never returns garbage terms.
"""
import json
import logging
import re

from backend.ai.gemini_client import generate

logger = logging.getLogger(__name__)

DEFAULT_FILTERS = {
    "search_terms": [],
    "location": "",
    "remote": False,
    "company_types": [],
    "domains": [],
    "exclusions": [],
    "seniority": "",
}


def _strip_json_fence(text: str) -> str:
    text = re.sub(r"^```json\s*", "", text.strip())
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_with_gemini(description: str, gemini_key: str) -> dict:
    prompt = f"""
You are a job search filter extractor. Given the user's job preference description below,
extract structured search filters as a JSON object.

Description:
{description}

Return ONLY a JSON object with these keys:
- search_terms: list of 3-5 concise job-title search strings for job boards
  (e.g. ["data scientist", "machine learning engineer", "MLOps engineer"])
- location: primary location string (e.g. "London, UK")
- remote: true/false whether remote is acceptable
- company_types: list of preferred company types (startup, enterprise, law firm, etc.)
- domains: list of specific domains/industries (fintech, healthcare, AI, etc.)
- exclusions: list of keywords to avoid in job titles or companies
- seniority: one of "junior", "mid", "senior", "any"

Return only valid JSON, no markdown, no explanation.
"""
    text = generate(gemini_key, prompt)
    if not text:
        logger.info("nl_parser: Gemini unavailable, using hardcoded fallback.")
        return hardcoded_fallback(description)

    try:
        filters = json.loads(_strip_json_fence(text))
        terms = filters.get("search_terms") or []
        if not terms:                       # empty terms → fall back
            return hardcoded_fallback(description)
        logger.info(f"nl_parser: {len(terms)} search terms via Gemini")
        return {**DEFAULT_FILTERS, **filters}
    except Exception as e:
        logger.warning(f"nl_parser: could not parse Gemini JSON ({e}). Falling back.")
        return hardcoded_fallback(description)


def hardcoded_fallback(description: str) -> dict:
    """
    Reliable fallback. Detects India vs UK from the description and returns
    sensible fixed search terms. Never returns garbage.
    """
    desc_lower = (description or "").lower()
    remote = any(w in desc_lower for w in ["remote", "hybrid", "wfh", "work from home"])

    india_signals = ["india", "mumbai", "delhi", "bangalore", "bengaluru",
                     "law firm", "litigation", "legal", "advocate", "naukri"]
    if any(w in desc_lower for w in india_signals):
        return {
            **DEFAULT_FILTERS,
            "search_terms": ["legal associate", "litigation associate",
                             "corporate lawyer", "law firm associate"],
            "location": "India",
            "remote": remote,
            "seniority": "any",
        }

    return {
        **DEFAULT_FILTERS,
        "search_terms": ["data scientist", "machine learning engineer",
                         "AI engineer", "MLOps engineer"],
        "location": "London, UK",
        "remote": remote,
        "seniority": "any",
    }


def get_search_filters(description: str, gemini_key: str = "") -> dict:
    if gemini_key:
        return parse_with_gemini(description, gemini_key)
    return hardcoded_fallback(description)
