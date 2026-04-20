from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.chat import Conversation, Message
from app.middleware.auth import require_admin
from app.services.llm_service import LLMService
from app.config import get_settings

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])
llm_service = LLMService()


@router.get("/stats")
async def get_stats(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar()
    conv_count = (await db.execute(select(func.count(Conversation.id)))).scalar()
    msg_count = (await db.execute(select(func.count(Message.id)))).scalar()
    positive_fb = (await db.execute(
        select(func.count(Message.id)).where(Message.feedback == 1)
    )).scalar()
    negative_fb = (await db.execute(
        select(func.count(Message.id)).where(Message.feedback == -1)
    )).scalar()
    return {
        "users": user_count,
        "documents": doc_count,
        "conversations": conv_count,
        "messages": msg_count,
        "feedback": {"positive": positive_fb, "negative": negative_fb},
    }


@router.get("/users")
async def list_users(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "full_name": u.full_name,
             "role": u.role, "is_active": u.is_active, "created_at": str(u.created_at)} for u in users]


@router.get("/models")
async def list_models(admin: User = Depends(require_admin)):
    return await llm_service.list_models()


# --- Global defaults management ---
import json
import redis.asyncio as aioredis
from pydantic import BaseModel

_settings = get_settings()


class GlobalDefaults(BaseModel):
    model: str | None = None
    embedding_model: str | None = None
    temperature: float | None = None
    top_k: int | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    max_tokens: int | None = None


@router.get("/defaults")
async def get_global_defaults(admin: User = Depends(require_admin)):
    r = aioredis.from_url(_settings.redis_url, decode_responses=True)
    raw = await r.get("prefs:global")
    await r.aclose()
    if raw:
        return json.loads(raw)
    return {
        "model": _settings.default_llm_model,
        "embedding_model": _settings.default_embedding_model,
        "temperature": _settings.temperature,
        "top_k": _settings.top_k,
        "chunk_size": _settings.chunk_size,
        "chunk_overlap": _settings.chunk_overlap,
        "max_tokens": _settings.max_tokens,
    }


@router.put("/defaults")
async def update_global_defaults(defaults: GlobalDefaults, admin: User = Depends(require_admin)):
    r = aioredis.from_url(_settings.redis_url, decode_responses=True)
    data = defaults.model_dump(exclude_none=True)
    # Merge with existing
    raw = await r.get("prefs:global")
    existing = json.loads(raw) if raw else {}
    existing.update(data)
    await r.set("prefs:global", json.dumps(existing))
    await r.aclose()
    return {"status": "ok", "defaults": existing}
