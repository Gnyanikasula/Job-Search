"""
routers/jobs.py — GET /jobs, PATCH /jobs/{id}/status
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def get_jobs(profile_id: str, status: str | None = None, days: int = 7):
    from backend.database.db import get_jobs
    return get_jobs(profile_id, status=status, days=days)


class StatusUpdate(BaseModel):
    status: str  # New | Applied | Skipped


@router.patch("/{job_id}/status")
def update_status(job_id: str, body: StatusUpdate):
    from backend.database.db import update_job_status
    update_job_status(job_id, body.status)
    return {"status": "updated"}


@router.get("/last-search/{profile_id}")
def last_search(profile_id: str):
    from backend.database.db import get_last_search
    return get_last_search(profile_id) or {}
