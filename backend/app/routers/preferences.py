import json
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.config import get_settings
from app.models.user import User
from app.middleware.auth import get_current_user

settings = get_settings()
router = APIRouter(prefix="/api/v1/preferences", tags=["Preferences"])

DEFAULTS = {
    "model": settings.default_llm_model,
    "embedding_model": settings.default_embedding_model,
    "temperature": settings.temperature,
    "top_k": settings.top_k,
    "chunk_size": settings.chunk_size,
    "chunk_overlap": settings.chunk_overlap,
    "max_tokens": settings.max_tokens,
}


class UserPreferences(BaseModel):
    model: str | None = None
    temperature: float | None = None
    top_k: int | None = None
    chunk_size: int | None = None
    max_tokens: int | None = None


async def _get_redis():
    return aioredis.from_url(settings.redis_url, decode_responses=True)


@router.get("")
async def get_preferences(user: User = Depends(get_current_user)):
    """Get merged preferences: global defaults < admin overrides < user prefs."""
    r = await _get_redis()
    admin_raw = await r.get("prefs:global")
    user_raw = await r.get(f"prefs:user:{user.id}")
    await r.aclose()

    result = {**DEFAULTS}
    if admin_raw:
        result.update({k: v for k, v in json.loads(admin_raw).items() if v is not None})
    if user_raw:
        result.update({k: v for k, v in json.loads(user_raw).items() if v is not None})
    return result


@router.put("")
async def update_preferences(prefs: UserPreferences, user: User = Depends(get_current_user)):
    """Save user-level preferences."""
    r = await _get_redis()
    data = prefs.model_dump(exclude_none=True)
    await r.set(f"prefs:user:{user.id}", json.dumps(data))
    await r.aclose()
    return {"status": "ok", "saved": data}


@router.get("/models")
async def list_available_models(user: User = Depends(get_current_user)):
    """List models available from Ollama (any authenticated user)."""
    from app.services.llm_service import LLMService
    svc = LLMService()
    return await svc.list_models()
