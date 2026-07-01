#!/bin/bash
# start.sh — container entrypoint
# Starts FastAPI on :8000 (background), then Streamlit on :7860 (foreground)
# Used by both Docker locally and HuggingFace Spaces.

set -e

echo "=== Job Search Pipeline starting ==="
echo "Python: $(python --version)"

# Ensure data directory exists (may be a mounted volume on HF)
mkdir -p /app/data

# ── Start FastAPI backend ──────────────────────────────────────────────────
echo "Starting FastAPI on :8000..."
uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level warning \
    &

BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Give the backend 3 seconds to initialise DB + scheduler
sleep 3

# Verify backend is up before starting frontend
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "ERROR: Backend failed to start. Check logs above."
    exit 1
fi
echo "Backend ready."

# ── Start Streamlit frontend ──────────────────────────────────────────────
echo "Starting Streamlit on :7860..."
exec streamlit run frontend/app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false \
    --server.enableCORS false \
    --server.enableXsrfProtection false
