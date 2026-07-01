"""
backend/main.py
FastAPI app entry point. Registers routers, initialises DB, starts scheduler.
"""
import warnings
warnings.filterwarnings("ignore")          # silence numpy MINGW noise on Windows

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
# Quieten noisy third-party loggers
for noisy in ("httpx", "google_genai", "apscheduler.executors.default"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database …")
    from backend.database.db import init_db
    init_db()
    logger.info("DB ready.")

    logger.info("Starting APScheduler …")
    from backend.scheduler import build_scheduler
    scheduler = build_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Scheduler running. Next fire: 06:00 UTC daily.")

    yield

    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped.")


app = FastAPI(title="Job Search Pipeline API", version="1.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

from backend.routers.search   import router as search_router
from backend.routers.profiles import router as profiles_router
from backend.routers.keys     import router as keys_router
from backend.routers.jobs     import router as jobs_router

app.include_router(search_router)
app.include_router(profiles_router)
app.include_router(keys_router)
app.include_router(jobs_router)


@app.get("/")
def health():
    return {"status": "ok", "service": "job-search-pipeline"}


@app.get("/health")
def health_check():
    from backend.database.db import get_conn
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}
