from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "DocMind"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://docmind:docmind_secret@localhost:5432/docmind"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8100

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    default_llm_model: str = "llama3.2"
    default_embedding_model: str = "nomic-embed-text"

    # Auth
    secret_key: str = "change-me-in-production-use-openssl-rand"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
    temperature: float = 0.7
    max_tokens: int = 2048

    # Upload
    upload_dir: str = "/app/uploads"
    max_file_size_mb: int = 50

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
