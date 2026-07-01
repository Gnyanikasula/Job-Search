"""
frontend/pages/3_Search.py — manual trigger + live progress
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
import streamlit as st
from frontend.utils import api, profile_selector, SEARCH_TIMEOUT

st.set_page_config(page_title="Run Search", page_icon="🔍", layout="wide")
st.title("🔍 Run Job Search")

profile_id = profile_selector()

last, _    = api("get", f"/jobs/last-search/{profile_id}")
profile, _ = api("get", f"/profiles/{profile_id}")
keys, _    = api("get", f"/keys/{profile_id}")

col1, col2, col3 = st.columns(3)
with col1:
    cv_ok = bool((profile or {}).get("cv_text", "").strip())
    st.metric("CV uploaded", "✅ Yes" if cv_ok else "❌ No")
with col2:
    desc_ok = bool((profile or {}).get("description", "").strip())
    st.metric("Job description", "✅ Set" if desc_ok else "❌ Not set")
with col3:
    key_ok = bool((keys or {}).get("gemini_key", ""))
    st.metric("Gemini key", "✅ Set" if key_ok else "⚪ Not set (scoring off)")

if not desc_ok:
    st.warning("Head to **Profile** first to write your job description. (CV is optional but enables scoring.)")

st.divider()
st.subheader("🕐 Scheduled run")
st.info(
    "The pipeline runs automatically at **06:00 UTC every day**. "
    "Use the button below only if you want a fresh fetch right now.",
    icon="🤖",
)

if last and last.get("ran_at"):
    ran = last["ran_at"].replace("T", " ").split(".")[0]
    line = (f"Last run: **{ran} UTC** | Trigger: {last.get('trigger', '?')} | "
            f"Found: {last.get('jobs_found', 0)} | New: {last.get('jobs_new', 0)}")
    if last.get("error"):
        line += f" | ⚠️ {last['error']}"
    st.caption(line)
else:
    st.caption("No run recorded yet for this profile.")

st.divider()
st.subheader("▶️ Fetch today's jobs now")

col_btn, col_note = st.columns([1, 3])
with col_btn:
    run_clicked = st.button("🚀 Fetch Now", type="primary", use_container_width=True)
with col_note:
    st.caption("Runs the full pipeline. Scraping + scoring can take 1–3 minutes. "
               "Leave this tab open until it finishes.")

if run_clicked:
    progress = st.progress(0, text="Starting pipeline…")
    status_box = st.empty()

    prep = [
        (15, "Parsing your job description into search filters…"),
        (35, "Searching Indeed and LinkedIn…"),
        (55, "Checking the YC startup feed…"),
        (70, "Deduplicating against the last 24 hours…"),
        (85, "Scoring new jobs against your CV…"),
    ]
    for pct, msg in prep:
        progress.progress(pct, text=msg)
        time.sleep(0.3)

    status_box.info("⏳ Pipeline running — this can take a couple of minutes…")
    result, err = api("post", "/search/sync",
                      json={"profile_id": profile_id, "trigger": "manual"},
                      timeout=SEARCH_TIMEOUT)

    progress.progress(100, text="Done!")

    if err:
        status_box.error(f"Pipeline error: {err}")
    elif result and result.get("error"):
        status_box.warning(
            f"Pipeline finished with a warning: {result['error']}. "
            f"Fetched {result.get('jobs_fetched', 0)}, stored {result.get('jobs_new', 0)}."
        )
    elif result:
        status_box.empty()
        st.success(
            f"✅ Done! **{result.get('jobs_fetched', 0)}** fetched, "
            f"**{result.get('jobs_new', 0)}** new, "
            f"**{result.get('jobs_scored', 0)}** scored."
        )
        if result.get("jobs_fetched", 0) == 0:
            st.info(
                "0 jobs came back. This is usually a scraper being rate-limited "
                "(especially LinkedIn/Indeed from a cloud IP) rather than a code bug. "
                "Try again in a minute, or check the backend logs for per-site counts.",
                icon="💡",
            )
        if result.get("search_terms"):
            st.caption(f"Search terms used: {', '.join(result['search_terms'])}")
        st.page_link("pages/4_Results.py", label="→ View ranked results", icon="📊")
