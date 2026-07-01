"""
app.py — HuggingFace Spaces entry point
Starts FastAPI + APScheduler in a background daemon thread, then Streamlit loads.
"""
import sys
import threading
import logging

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def start_backend():
    import uvicorn
    from backend.main import app as fastapi_app
    logger.info("Starting FastAPI backend on :8000 …")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="warning")


# Start FastAPI in background thread (daemon so it dies with the process)
thread = threading.Thread(target=start_backend, daemon=True)
thread.start()

# Give backend a moment to initialise before Streamlit starts
import time
time.sleep(2)

logger.info("Backend thread started. Streamlit loading …")
