import asyncio
import uuid
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session
from app.tasks.worker import celery_app
from app.config import get_settings
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.models.document import Document

settings = get_settings()

# Sync engine for Celery workers
sync_db_url = settings.database_url.replace("+asyncpg", "+psycopg2")
sync_engine = create_engine(sync_db_url)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def ingest_document(self, document_id: str, file_path: str, file_type: str):
    """Process and ingest a document into the vector store."""
    processor = DocumentProcessor()
    embedding_service = EmbeddingService()

    with Session(sync_engine) as db:
        try:
            # Update status to processing
            db.execute(update(Document).where(
                Document.id == uuid.UUID(document_id)
            ).values(status="processing"))
            db.commit()

            # Extract text
            text, page_count = processor.extract_text(file_path, file_type)
            if not text.strip():
                raise ValueError("No text content extracted from document")

            # Chunk text
            chunks = processor.chunk_text(text)
            if not chunks:
                raise ValueError("Document produced no chunks")

            # Generate collection name
            collection_name = f"doc_{document_id.replace('-', '_')}"

            # Build metadata for each chunk
            metadatas = []
            ids = []
            for i, chunk in enumerate(chunks):
                metadatas.append({
                    "document_id": document_id,
                    "chunk_index": i,
                    "page_number": min(i + 1, page_count) if page_count else None,
                    "token_count": processor.count_tokens(chunk),
                })
                ids.append(f"{document_id}_chunk_{i}")

            # Store embeddings
            _run_async(embedding_service.store_chunks(
                collection_name, chunks, metadatas, ids
            ))

            # Update document record
            db.execute(update(Document).where(
                Document.id == uuid.UUID(document_id)
            ).values(
                status="ready",
                page_count=page_count,
                chunk_count=len(chunks),
                collection_id=collection_name,
            ))
            db.commit()

        except Exception as exc:
            db.execute(update(Document).where(
                Document.id == uuid.UUID(document_id)
            ).values(status="failed", error_message=str(exc)))
            db.commit()
            raise self.retry(exc=exc)
