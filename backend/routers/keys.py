"""
routers/keys.py — GET/POST /keys
Resets Gemini model cache when the key is updated.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/keys", tags=["keys"])


class KeysPayload(BaseModel):
    profile_id: str
    gemini_key: str = ""
    groq_key: str = ""
    serper_key: str = ""


@router.get("/{profile_id}")
def get_keys(profile_id: str):
    from backend.database.db import get_keys
    keys = get_keys(profile_id)
    def mask(k): return k[:6] + "…" if len(k) > 6 else ("set" if k else "")
    return {
        "profile_id": profile_id,
        "gemini_key":  mask(keys.get("gemini_key", "")),
        "groq_key":    mask(keys.get("groq_key", "")),
        "serper_key":  mask(keys.get("serper_key", "")),
    }


@router.post("")
def save_keys(payload: KeysPayload):
    from backend.database.db import save_keys
    from backend.ai.gemini_client import reset_model_cache
    save_keys(payload.profile_id, payload.gemini_key,
              payload.groq_key, payload.serper_key)
    # Changing the key means old cached model discovery is invalid
    reset_model_cache()
    return {"status": "saved"}
