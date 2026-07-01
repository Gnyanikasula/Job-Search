"""
frontend/pages/2_Profile.py — CV upload + natural language job description
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from frontend.utils import api, profile_selector

st.set_page_config(page_title="My Profile", page_icon="📋", layout="wide")
st.title("📋 My Profile")

profile_id = profile_selector()

# Load current profile
profile, err = api("get", f"/profiles/{profile_id}")
if err:
    st.error(f"Backend error: {err}")
    st.stop()

col_left, col_right = st.columns([1, 1], gap="large")

# ── CV upload ─────────────────────────────────────────────────────────────────
with col_left:
    st.subheader("📄 CV / Resume")
    st.caption("Paste or upload your CV. The system uses this to score every job against your background.")

    current_cv = profile.get("cv_text", "") if profile else ""
    has_cv = bool(current_cv.strip())

    if has_cv:
        st.success(f"✅ CV on file — {len(current_cv):,} characters")
        with st.expander("Preview CV text"):
            st.text(current_cv[:1000] + ("…" if len(current_cv) > 1000 else ""))
    else:
        st.warning("No CV uploaded yet. Scoring will be skipped until you add one.")

    # Upload tab or paste tab
    tab_upload, tab_paste = st.tabs(["Upload PDF/TXT", "Paste text"])

    with tab_upload:
        uploaded = st.file_uploader("Upload CV", type=["txt", "pdf"])
        if uploaded:
            if uploaded.type == "application/pdf":
                try:
                    import pdfplumber
                    with pdfplumber.open(uploaded) as pdf:
                        cv_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
                except ImportError:
                    st.error("pdfplumber not installed. Use the paste tab instead.")
                    cv_text = ""
            else:
                cv_text = uploaded.read().decode("utf-8", errors="ignore")

            if cv_text.strip():
                if st.button("💾 Save uploaded CV", type="primary"):
                    _, err = api("post", f"/profiles/{profile_id}",
                                 json={"cv_text": cv_text})
                    if err:
                        st.error(err)
                    else:
                        st.success("CV saved!")
                        st.rerun()

    with tab_paste:
        pasted = st.text_area("Paste CV text here", height=300,
                              value=current_cv, placeholder="Paste full CV text…")
        if st.button("💾 Save pasted CV", type="primary", key="save_paste"):
            _, err = api("post", f"/profiles/{profile_id}", json={"cv_text": pasted})
            if err:
                st.error(err)
            else:
                st.success("CV saved!")
                st.rerun()

# ── Job description ───────────────────────────────────────────────────────────
with col_right:
    st.subheader("🎯 What jobs are you looking for?")
    st.caption(
        "Describe your ideal job in plain English. The AI will turn this into search filters. "
        "Be specific — mention roles, industries, company sizes, location preferences, etc."
    )

    examples = {
        "gnyani": (
            "I'm looking for AI/ML engineer or data scientist roles in London or remote UK. "
            "Preferably startups or scale-ups in fintech or healthcare. I want roles that involve "
            "building production ML systems, not just research. Python, PyTorch, and MLOps skills are my strengths. "
            "Avoid roles requiring more than 5 years experience or requiring security clearance."
        ),
        "friend": (
            "I'm looking for litigation or corporate law associate roles at law firms in India, "
            "primarily in Mumbai or Delhi. I'm open to legal internships at top-tier firms. "
            "Interested in M&A, dispute resolution, or regulatory law. Avoid in-house positions for now."
        ),
    }

    current_desc = (profile.get("description", "") if profile else "") or examples.get(profile_id, "")
    current_loc  = (profile.get("location", "")    if profile else "")

    description = st.text_area(
        "Job description (natural language)",
        value=current_desc,
        height=220,
        placeholder="e.g. I'm a data scientist looking for ML roles in London…",
    )

    location = st.text_input(
        "Primary location",
        value=current_loc or ("London, UK" if profile_id == "gnyani" else "India"),
        help="Used as a fallback if not mentioned in the description"
    )

    country = st.selectbox(
        "Country / portal set",
        ["UK", "India"],
        index=0 if profile_id == "gnyani" else 1,
    )

    if st.button("💾 Save profile", type="primary"):
        _, err = api("post", f"/profiles/{profile_id}", json={
            "description": description,
            "location": location,
            "country": country,
        })
        if err:
            st.error(err)
        else:
            st.success("✅ Profile saved! Changes take effect on the next search run.")

    st.divider()
    st.caption("💡 Tip: After updating your description, go to the Search page and click **Fetch Now** to apply the new filters immediately.")
