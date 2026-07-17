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

Fetches, scores, and ranks fresh jobs every morning. You apply manually to the top 10–20.

## First-time setup

1. **⚙️ Settings** — paste your Gemini API key (free at aistudio.google.com)
2. **📋 Profile** — upload CV + write your job description in plain English
3. **🔍 Search** — click Fetch Now
4. **📊 Results** — review ranked jobs, click apply links, mark status

## Stack

FastAPI · Streamlit · python-jobspy · google-genai · SQLite · APScheduler

**Total cost: £0.00**

## ⚠️ Storage note

HuggingFace free tier uses **ephemeral storage** — the SQLite database resets
when the Space restarts. API keys and profile will need to be re-entered once
after a restart. Jobs are re-fetched on the next scheduled run.

To avoid this, upgrade to a persistent-storage HF Space or self-host with Docker.
