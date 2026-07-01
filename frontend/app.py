"""
frontend/app.py — Streamlit home page / entry point
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Job Search Pipeline",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎯 AI Job Search Pipeline")
st.caption("Your daily job briefing — automated, scored, ranked.")

st.markdown("""
## How it works

| Step | What happens |
|------|-------------|
| **06:00 UTC daily** | Scheduler auto-fetches fresh jobs from LinkedIn, Indeed, Glassdoor, Google Jobs, YC Jobs |
| **Morning** | You open this app — ranked list is already waiting |
| **You review** | Each job has a score 0–100, skill match, gaps, and red flags |
| **You apply** | Click the direct apply link for your top 10–20. Mark as Applied. Done. |

## Quick start

1. **⚙️ Settings** — add your Gemini API key (free, 1,500 req/day)
2. **📋 Profile** — upload your CV and describe your ideal job in plain English  
3. **🔍 Search** — click Fetch Now for your first run
4. **📊 Results** — review ranked jobs and start applying

---
""")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Gnyani — UK AI/ML")
    st.write("Searches: LinkedIn, Indeed, Glassdoor, Google Jobs, YC Jobs")
    st.write("Location: London + Remote UK")
    st.write("Target: Data Scientist / ML Engineer / AI Engineer roles")

with col2:
    st.subheader("Friend — India Legal")
    st.write("Searches: LinkedIn India, Indeed India, Naukri")
    st.write("Location: Mumbai, Delhi, Bangalore")
    st.write("Target: Litigation / Corporate Law Associate roles")

st.divider()
st.caption("Total cost: £0.00 · Stack: FastAPI + Streamlit + JobSpy + Gemini + SQLite + HuggingFace")
