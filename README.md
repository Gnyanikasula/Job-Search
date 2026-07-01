---
title: AI Job Search Pipeline
emoji: 🎯
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# AI Job Search Pipeline

Auto-fetches, scores, and ranks fresh jobs every morning across LinkedIn, Indeed, and more.
You review the ranked list and apply manually to the top 10–20.

**Total cost: £0.00** | Stack: FastAPI · Streamlit · python-jobspy · Gemini · SQLite

---

## ⚠️ HuggingFace Spaces note

Storage is **ephemeral** — SQLite resets on every Space restart. You'll need to
re-enter your API keys and profile once after each restart. A warning banner in the
UI makes this visible.

---

## Local setup

**Prerequisites:** Python 3.11+, Docker (optional but recommended)

### Option A — Docker (recommended, matches HF exactly)

```bash
git clone <your-repo>
cd job-search-app
docker compose up --build
```
Open http://localhost:7860

### Option B — Raw Python

```bash
pip install -r requirements.txt
playwright install chromium

# Terminal 1 — backend (no --reload)
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
streamlit run frontend/app.py --server.port 7860
```

> ⚠️ Never run the backend with `--reload`. The pipeline writes to SQLite and
> uvicorn's reload watcher will restart the server mid-request, causing
> "Cannot reach backend" in the UI.

---

## First-time setup (in the app)

1. **⚙️ Settings** → paste your Gemini key (free at aistudio.google.com, AI Studio, no billing)
2. **📋 Profile** → upload your CV + write your job description in plain English
3. **🔍 Search** → click **Fetch Now**
4. **📊 Results** → ranked list, apply to top 10–20, mark as Applied

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Cannot reach backend" | Backend crashed or `--reload` restarted it | Check backend terminal; restart without `--reload` |
| 0 jobs fetched | Scraper rate-limited by LinkedIn/Indeed | Retry; check backend logs for per-site counts |
| Gemini model 404 | Retired model name | Fixed — app auto-discovers models at runtime |
| Gemini 429 `limit: 0` | Key's project has free tier disabled | New key from AI Studio, project without billing |
| numpy crash on Windows | Broken MINGW build | `pip install "numpy>=2.2" --only-binary=:all:` |

---

## Phase roadmap

| Phase | Status |
|-------|--------|
| 1 — Skeleton: FastAPI + Streamlit + JobSpy + Scheduler | ✅ Done |
| 2 — AI layer: Gemini scoring + caching + auto-discovery | ✅ Done |
| 3 — More scrapers: Wellfound, Otta, Reed, LawCtopus… | Next |
| 4 — Serper enrichment + status tracking polish | Planned |
