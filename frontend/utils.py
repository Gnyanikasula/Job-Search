"""
frontend/utils.py — shared helpers for all Streamlit pages
"""
import os
import requests
import streamlit as st

# In Docker the backend runs in the same container on :8000.
# Locally it's also :8000. Never changes.
API_BASE = os.environ.get("API_BASE", "http://localhost:8000")

PROFILES = {
    "gnyani": "Gnyani (UK — AI/ML)",
    "friend": "Friend (India — Legal)",
}

DEFAULT_TIMEOUT = 30
SEARCH_TIMEOUT  = 600   # pipeline can take up to 10 min with JD fetching + scoring


def api(method: str, path: str, timeout: int = DEFAULT_TIMEOUT, **kwargs):
    """Thin wrapper. Returns (data, error_or_None)."""
    try:
        resp = getattr(requests, method)(
            f"{API_BASE}{path}", timeout=timeout, **kwargs
        )
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot reach backend. Is the FastAPI server running on :8000?"
    except requests.exceptions.ReadTimeout:
        return None, (
            "Pipeline is still running (took longer than expected). "
            "Check the backend terminal — it may have finished. "
            "Refresh Results to see if jobs appeared."
        )
    except Exception as e:
        return None, str(e)


def profile_selector(key="selected_profile"):
    st.sidebar.title("👤 Profile")
    return st.sidebar.radio(
        "Select profile",
        options=list(PROFILES.keys()),
        format_func=lambda x: PROFILES[x],
        key=key,
    )


def score_color(score: int) -> str:
    if score >= 75: return "🟢"
    if score >= 50: return "🟡"
    if score >= 0:  return "🔴"
    return "⚪"


def score_badge(score: int) -> str:
    return f"{score_color(score)} {score if score >= 0 else '—'}"
