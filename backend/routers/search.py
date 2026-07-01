"""
routers/search.py — POST /search (background) and POST /search/sync (blocking)
"""
from fastapi import APIRouter, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    profile_id: str
    trigger: str = "manual"


@router.post("")
def trigger_search(req: SearchRequest, background_tasks: BackgroundTasks):
    """Fire-and-forget. Pipeline runs in the background; returns immediately."""
    from backend.scheduler import run_daily_search
    background_tasks.add_task(run_daily_search, req.profile_id, req.trigger)
    return {"status": "started", "profile_id": req.profile_id}


@router.post("/sync")
async def trigger_search_sync(req: SearchRequest):
    """
    Blocking version used by the Streamlit 'Fetch Now' button.
    Runs the (synchronous) pipeline in a threadpool so it doesn't block the
    FastAPI event loop, then returns the full summary.
    """
    from backend.scheduler import run_daily_search
    result = await run_in_threadpool(run_daily_search, req.profile_id, req.trigger)
    return result
