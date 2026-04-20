from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    file_size: int
    page_count: int | None
    chunk_count: int
    status: str
    error_message: str | None
    tags: list[str]
    folder: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    tags: list[str] | None = None
    folder: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class IngestionStatus(BaseModel):
    document_id: UUID
    status: str
    chunk_count: int
    error_message: str | None = None
