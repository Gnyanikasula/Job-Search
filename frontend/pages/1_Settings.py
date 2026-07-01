"""
frontend/pages/1_Settings.py — API key management
Keys can be entered here (stored in SQLite) OR set as environment variables
(HuggingFace Spaces secrets / Docker env). Env vars take priority.
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from frontend.utils import api, profile_selector

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.title("⚙️ Settings — API Keys")

# Detect if we're running in Docker / HF
env_gemini = bool(os.environ.get("GEMINI_API_KEY"))
env_groq   = bool(os.environ.get("GROQ_API_KEY"))
env_serper = bool(os.environ.get("SERPER_API_KEY"))

if env_gemini or env_groq or env_serper:
    st.success(
        "✅ **Environment variables detected.** Keys are loaded from Docker/HuggingFace secrets. "
        "You don't need to enter them below.",
        icon="🔒"
    )
else:
    st.info(
        "**Keys are stored in local SQLite only.** On HuggingFace Spaces, add them as "
        "Repository Secrets instead (Settings → Repository secrets). "
        "On Docker, pass them as environment variables.",
        icon="ℹ️"
    )

profile_id = profile_selector()
data, err = api("get", f"/keys/{profile_id}")
if err:
    st.error(f"Backend error: {err}")
    st.stop()

st.subheader(f"Current key status — {profile_id}")
col1, col2, col3 = st.columns(3)
with col1:
    val = "🌍 From env" if env_gemini else (data.get("gemini_key") or "❌ Not set")
    st.metric("Gemini Key", val)
with col2:
    val = "🌍 From env" if env_groq else (data.get("groq_key") or "❌ Not set")
    st.metric("Groq Key", val)
with col3:
    val = "🌍 From env" if env_serper else (data.get("serper_key") or "❌ Not set")
    st.metric("Serper Key", val)

st.divider()
st.subheader("Enter / update keys manually")

with st.form("keys_form"):
    gemini = st.text_input(
        "Gemini API Key",
        type="password",
        help="Free at aistudio.google.com — 1,500 req/day. App auto-discovers the right model.",
        placeholder="AIza…",
    )
    groq = st.text_input(
        "Groq API Key (fallback scorer)",
        type="password",
        help="Free at console.groq.com",
        placeholder="gsk_…",
    )
    serper = st.text_input(
        "Serper.dev Key (company research)",
        type="password",
        help="Free at serper.dev — 2,500 queries",
    )
    if st.form_submit_button("💾 Save Keys", type="primary"):
        payload = {
            "profile_id": profile_id,
            "gemini_key": gemini,
            "groq_key": groq,
            "serper_key": serper,
        }
        _, err = api("post", "/keys", json=payload)
        if err:
            st.error(f"Save failed: {err}")
        else:
            st.success("✅ Keys saved!")
            st.rerun()

st.divider()
st.subheader("🔑 Where to get free keys")
rows = [
    ("Gemini", "aistudio.google.com", "1,500 req/day free — NL parsing + scoring. Create key in a project WITHOUT billing."),
    ("Groq",   "console.groq.com",    "Generous free tier — fallback scorer"),
    ("Serper", "serper.dev",           "2,500 total free queries — company research"),
]
for name, url, desc in rows:
    st.markdown(f"**{name}** — `{url}` — {desc}")
