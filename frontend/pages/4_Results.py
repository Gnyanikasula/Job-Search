"""
frontend/pages/4_Results.py — ranked job dashboard
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from frontend.utils import api, profile_selector, score_badge, score_color

st.set_page_config(page_title="Results", page_icon="📊", layout="wide")
st.title("📊 Today's Jobs")

profile_id = profile_selector()

# ── filter bar ────────────────────────────────────────────────────────────────
col_view, col_days, col_score = st.columns([2, 1, 1])
with col_view:
    view = st.radio("Show", ["New", "Applied", "Skipped", "All"],
                    horizontal=True, index=0)
with col_days:
    days = st.selectbox("Last N days", [1, 3, 7, 14], index=2)
with col_score:
    min_score = st.slider("Min score", 0, 100, 0)

# ── fetch ─────────────────────────────────────────────────────────────────────
status_param = None if view == "All" else view
qs = f"profile_id={profile_id}&days={days}"
if status_param:
    qs += f"&status={status_param}"

jobs, err = api("get", f"/jobs?{qs}")
if err:
    st.error(f"Could not load jobs: {err}")
    st.stop()

if not jobs:
    st.info(
        "No jobs found yet. Go to **🔍 Search** and click Fetch Now.",
        icon="💡"
    )
    st.page_link("pages/3_Search.py", label="→ Go to Search", icon="🔍")
    st.stop()

if min_score > 0:
    jobs = [j for j in jobs if j.get("score", -1) >= min_score]

scored_count   = sum(1 for j in jobs if j.get("score", -1) >= 0)
enriched_count = sum(1 for j in jobs if len(j.get("description", "")) >= 500)

st.caption(
    f"**{len(jobs)}** jobs · "
    f"**{scored_count}** scored · "
    f"**{enriched_count}** with full JD · "
    f"sorted by score"
)
st.divider()

# ── job cards ─────────────────────────────────────────────────────────────────
for job in jobs:
    score = job.get("score", -1)
    raw   = job.get("score_data", "{}")
    try:
        score_data = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        score_data = {}

    c_title, c_score, c_status = st.columns([5, 1, 1.5])

    with c_title:
        title   = job.get("title", "Unknown Role")
        company = job.get("company", "")
        loc     = job.get("location", "")
        source  = job.get("source", "")
        url     = job.get("url", "") or job.get("job_url", "")
        jd_len  = len(job.get("description", ""))
        jd_tag  = "📄" if jd_len >= 500 else "📋"

        if url:
            st.markdown(f"### [{title}]({url})")
        else:
            st.markdown(f"### {title}")
        st.caption(f"**{company}** · {loc} · via {source} · {jd_tag} JD {'full' if jd_len >= 500 else 'snippet'}")

    with c_score:
        st.markdown(f"## {score_badge(score)}")
        verdict = score_data.get("verdict", "")
        if verdict and verdict not in ("Not scored", "No Gemini key — scoring skipped"):
            st.caption(verdict)

    with c_status:
        job_id = job.get("id", "")
        current = job.get("status", "New")
        options = ["New", "Applied", "Skipped"]
        new_status = st.selectbox(
            "Status", options,
            index=options.index(current) if current in options else 0,
            key=f"status_{job_id}",
            label_visibility="collapsed",
        )
        if new_status != current and job_id:
            api("patch", f"/jobs/{job_id}/status", json={"status": new_status})
            st.rerun()

    # Score breakdown
    if score_data and score >= 0:
        with st.expander("🔍 Score breakdown", expanded=False):
            d1, d2 = st.columns(2)
            with d1:
                matched = score_data.get("matched_skills", [])
                if matched:
                    st.markdown("**✅ Matched skills**")
                    st.write(", ".join(matched))
                missing = score_data.get("missing_skills", [])
                if missing:
                    st.markdown("**📚 Missing skills**")
                    st.write(", ".join(missing))
            with d2:
                gap = score_data.get("experience_gap", "")
                if gap:
                    st.markdown("**⚠️ Experience gap**")
                    st.write(gap)
                flags = score_data.get("red_flags", [])
                if flags:
                    st.markdown("**🚩 Red flags**")
                    for f in flags:
                        st.write(f"• {f}")
            focus = score_data.get("cover_letter_focus", "")
            if focus:
                st.markdown("**✉️ Cover letter focus**")
                st.info(focus)

    # JD preview (if full JD was fetched)
    jd = job.get("description", "")
    if jd and len(jd) >= 500:
        with st.expander("📄 Job description preview", expanded=False):
            st.text(jd[:1500] + ("…" if len(jd) > 1500 else ""))

    st.divider()

# ── sidebar stats ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("📈 Summary")
    green    = sum(1 for j in jobs if j.get("score", -1) >= 75)
    amber    = sum(1 for j in jobs if 50 <= j.get("score", -1) < 75)
    red      = sum(1 for j in jobs if 0 <= j.get("score", -1) < 50)
    unscored = sum(1 for j in jobs if j.get("score", -1) < 0)
    applied  = sum(1 for j in jobs if j.get("status") == "Applied")

    st.metric("Total shown",         len(jobs))
    st.metric("🟢 Strong match ≥75", green)
    st.metric("🟡 Possible 50–74",   amber)
    st.metric("🔴 Weak <50",         red)
    if unscored:
        st.metric("⚪ Not scored",   unscored)
    st.divider()
    st.metric("📨 Applied",          applied)
