"""
ai/gemini_client.py
Shared Gemini client with runtime model auto-discovery and quota management.

Key behaviours:
- Auto-discovers available Flash model at runtime (never hardcodes a name)
- On 429 per-MINUTE: waits the retry delay, then continues
- On 429 per-DAY (daily quota exhausted): stops ALL calls for this process lifetime
- On 404/auth error: clears model cache so next call re-discovers
- Never resets model cache on 429 (avoids burning quota on re-discovery)
"""
import logging
import re
import threading
import time

logger = logging.getLogger(__name__)

_PREFERRED_FRAGMENTS = [
    "flash-latest",
    "3.5-flash",
    "3.1-flash",
    "2.5-flash",
    "2.0-flash",
    "flash",
]

_cached_model: str | None = None
_lock = threading.Lock()

# Once we hit a daily quota error, stop ALL calls until process restart
_daily_quota_exhausted = False


def _get_client(api_key: str):
    from google import genai  # type: ignore
    return genai.Client(api_key=api_key)


def _is_daily_quota_error(e: Exception) -> bool:
    msg = str(e)
    return "PerDay" in msg or "per_day" in msg.lower() or "GenerateRequestsPerDay" in msg


def _is_per_minute_quota_error(e: Exception) -> bool:
    msg = str(e)
    return "429" in msg and not _is_daily_quota_error(e)


def _extract_retry_delay(e: Exception) -> int:
    """Parse the retryDelay seconds from the 429 error message."""
    match = re.search(r"retryDelay.*?(\d+)s", str(e))
    return int(match.group(1)) + 2 if match else 60


def discover_model(api_key: str) -> str | None:
    global _cached_model
    if _cached_model:
        return _cached_model
    with _lock:
        if _cached_model:
            return _cached_model
        try:
            client = _get_client(api_key)
            available = []
            for m in client.models.list():
                actions = getattr(m, "supported_actions", None) or []
                if "generateContent" in actions:
                    name = m.name.split("/")[-1] if m.name else ""
                    if name and "flash" in name.lower():
                        available.append(name)

            if not available:
                logger.warning("No Flash models with generateContent on this key.")
                return None

            for frag in _PREFERRED_FRAGMENTS:
                for name in available:
                    if frag in name.lower():
                        _cached_model = name
                        logger.info(f"Gemini model selected: {name}")
                        return name

            _cached_model = available[0]
            logger.info(f"Gemini model selected (fallback): {available[0]}")
            return _cached_model

        except Exception as e:
            logger.warning(f"Model discovery failed: {e}")
            return None


def generate(api_key: str, prompt: str, max_retries: int = 1) -> str | None:
    """
    Run a prompt. Returns text or None.
    - Daily quota exhausted → returns None immediately, logs once.
    - Per-minute 429 → waits retry delay and tries once more.
    - Other errors → returns None.
    Never raises.
    """
    global _daily_quota_exhausted, _cached_model

    if _daily_quota_exhausted:
        logger.debug("Daily quota exhausted — skipping Gemini call.")
        return None

    model = discover_model(api_key)
    if not model:
        return None

    for attempt in range(max_retries + 1):
        try:
            client = _get_client(api_key)
            response = client.models.generate_content(model=model, contents=prompt)
            return (response.text or "").strip()

        except Exception as e:
            if _is_daily_quota_error(e):
                _daily_quota_exhausted = True
                logger.warning(
                    "Daily Gemini quota exhausted (limit reached for today). "
                    "Remaining jobs will show as 'Not scored'. "
                    "Quota resets at midnight Pacific time."
                )
                return None

            if "404" in str(e) or "NOT_FOUND" in str(e):
                # Model retired — clear cache so next call re-discovers
                logger.warning(f"Model {model} not found — clearing cache for re-discovery.")
                _cached_model = None
                return None

            if "429" in str(e) and attempt < max_retries:
                delay = _extract_retry_delay(e)
                logger.info(f"Rate limited (per-minute). Waiting {delay}s then retrying…")
                time.sleep(delay)
                continue

            logger.warning(f"Gemini generate failed: {e}")
            return None

    return None


def reset_model_cache():
    """Call this when the API key changes in Settings."""
    global _cached_model, _daily_quota_exhausted
    _cached_model = None
    _daily_quota_exhausted = False
    logger.info("Gemini model cache reset.")


def quota_exhausted() -> bool:
    return _daily_quota_exhausted
