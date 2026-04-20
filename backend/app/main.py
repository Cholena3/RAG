from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import auth, documents, chat, admin
from app.routers import preferences
from app.middleware.auth import hash_password
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed admin
    await init_db()
    await _seed_admin()
    yield


async def _seed_admin():
    from app.database import async_session
    from app.models.user import User
    from sqlalchemy import select
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == "admin@docmind.io"))
        if not result.scalar_one_or_none():
            admin = User(
                email="admin@docmind.io",
                hashed_password=hash_password("admin123"),
                full_name="Admin",
                role="admin",
            )
            db.add(admin)
            await db.commit()


app = FastAPI(
    title="DocMind API",
    description="Intelligent Document Q&A Platform — RAG-powered",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(preferences.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "docmind"}
