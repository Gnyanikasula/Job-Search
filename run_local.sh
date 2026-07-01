#!/usr/bin/env bash
# run_local.sh — start the full stack locally (Linux/Mac)
set -e
echo "=== Job Search Pipeline — Local Dev ==="

if [ ! -f "requirements.txt" ]; then
  echo "ERROR: run this from the job-search-app/ directory"; exit 1
fi

# IMPORTANT: no --reload. The pipeline writes to data/jobs.db, and uvicorn's
# reload watcher would restart the server mid-request, dropping the connection.
echo "Starting FastAPI backend on :8000 (no reload) …"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 2

echo "Starting Streamlit on :8501 …"
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 \
  --browser.gatherUsageStats false

kill $BACKEND_PID 2>/dev/null
