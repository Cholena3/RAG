import json
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from app.database import get_db
from app.models.user import User
from app.models.chat import Conversation, Message
from app.schemas.chat import (
    ChatRequest, ChatResponse, ConversationResponse,
    ConversationListResponse, FeedbackRequest,
)
from app.middleware.auth import get_current_user
from app.services.rag_engine import RAGEngine

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
rag_engine = RAGEngine()


@router.post("", response_model=ChatResponse)
async def chat(data: ChatRequest, user: User = Depends(get_current_user),
               db: AsyncSession = Depends(get_db)):
    # Get or create conversation
    if data.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == data.conversation_id,
                Conversation.owner_id == user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(owner_id=user.id, model=data.model)
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)

    # Save user message
    user_msg = Message(conversation_id=conversation.id, role="user", content=data.query)
    db.add(user_msg)
    await db.flush()

    # Run RAG pipeline with conversation memory
    answer, citations, follow_ups, latency_ms, input_tokens, output_tokens = await rag_engine.answer(
        query=data.query,
        user_id=user.id,
        db=db,
        conversation_id=conversation.id,
        document_ids=data.document_ids,
        model=data.model,
        temperature=data.temperature,
        top_k=data.top_k,
    )

    # Save assistant message with token tracking
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources=json.dumps([c.model_dump() for c in citations]),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )
    db.add(assistant_msg)
    await db.flush()
    await db.refresh(assistant_msg)

    # Update conversation title from first question
    if conversation.title == "New Conversation":
        conversation.title = data.query[:100]

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        content=answer,
        sources=citations,
        follow_up_suggestions=follow_ups,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )


@router.post("/stream")
async def chat_stream(data: ChatRequest, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """SSE streaming endpoint for chat responses."""
    # Build conversation memory
    conv_history = await rag_engine._build_conversation_history(
        data.conversation_id, db, data.model
    )
    # Retrieve context
    citations = await rag_engine.retrieve_context(
        data.query, user.id, db, data.document_ids, data.top_k
    )
    prompt = rag_engine._build_prompt(data.query, citations, conv_history)

    async def event_generator():
        yield {"event": "sources", "data": json.dumps([c.model_dump() for c in citations])}
        full_response = ""
        async for token in rag_engine.llm_service.generate_stream(
            prompt, data.model, data.temperature
        ):
            full_response += token
            yield {"event": "token", "data": token}
        yield {"event": "done", "data": json.dumps({"content": full_response})}

    return EventSourceResponse(event_generator())


@router.get("/history", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (select(Conversation)
            .where(Conversation.owner_id == user.id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip).limit(limit))
    count_stmt = select(func.count(Conversation.id)).where(Conversation.owner_id == user.id)
    result = await db.execute(stmt)
    total = (await db.execute(count_stmt)).scalar()
    return ConversationListResponse(conversations=result.scalars().all(), total=total)


@router.get("/history/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: uuid.UUID, user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.owner_id == user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/history/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: uuid.UUID, user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.owner_id == user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)


@router.post("/feedback")
async def submit_feedback(data: FeedbackRequest, user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(Message.id == data.message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.feedback = data.feedback
    return {"status": "ok"}
