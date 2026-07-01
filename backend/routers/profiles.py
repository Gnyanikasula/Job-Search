"""
routers/profiles.py — GET/POST /profiles
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("")
def list_profiles():
    from backend.database.db import get_all_profiles
    return get_all_profiles()


@router.get("/{profile_id}")
def get_profile(profile_id: str):
    from backend.database.db import get_profile
    p = get_profile(profile_id)
    return p or {"error": "not found"}


class ProfileUpdate(BaseModel):
    name: str | None = None
    cv_text: str | None = None
    description: str | None = None
    location: str | None = None
    country: str | None = None


@router.post("/{profile_id}")
def update_profile(profile_id: str, body: ProfileUpdate):
    from backend.database.db import update_profile
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    update_profile(profile_id, **updates)
    return {"status": "updated"}
