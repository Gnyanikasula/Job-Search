"""
start.py — Docker/HuggingFace entry point.
Starts FastAPI (port 8000) in a background thread,
then launches Streamlit (port 7860) in the foreground.

HuggingFace Spaces requires the app to bind on port 7860.
FastAPI stays internal (8000) and is only called by Streamlit's localhost requests.
"""
import os
import subprocess
import sys
import threading
import time
import logging

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def start_backend():
    """Run FastAPI + APScheduler in a background thread."""
    import uvicorn
    from backend.main import app as fastapi_app
    logger.info("Starting FastAPI backend on :8000 …")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="warning")


def main():
    # Start FastAPI in daemon thread
    thread = threading.Thread(target=start_backend, daemon=True)
    thread.start()

    # Give the backend a moment to initialise
    logger.info("Waiting for backend to initialise…")
    time.sleep(4)

    # Launch Streamlit on port 7860 (HF requirement)
    logger.info("Starting Streamlit on :7860 …")
    streamlit_cmd = [
        sys.executable, "-m", "streamlit", "run",
        "frontend/app.py",
        "--server.port", "7860",
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
    ]

    proc = subprocess.run(streamlit_cmd)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
