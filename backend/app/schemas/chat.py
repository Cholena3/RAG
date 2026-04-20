from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ChatRequest(BaseModel):
    query: str
    conversation_id: UUID | None = None
    model: str | None = None
    temperature: float | None = None
    top_k: int | None = None
    document_ids: list[UUID] | None = None  # scope to specific docs


class SourceCitation(BaseModel):
    document_id: str
    document_name: str
    page_number: int | None = None
    chunk_text: str
    relevance_score: float


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    content: str
    sources: list[SourceCitation]
    follow_up_suggestions: list[str]
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    sources: str | None
    feedback: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    model: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class FeedbackRequest(BaseModel):
    message_id: UUID
    feedback: int  # 1 or -1
