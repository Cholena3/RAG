import json
import time
from uuid import UUID
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models.document import Document
from app.models.chat import Message
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.schemas.chat import SourceCitation

settings = get_settings()

SYSTEM_PROMPT = """You are DocMind, an intelligent document assistant. Answer the user's question based ONLY on the provided context. If the context doesn't contain enough information, say so honestly. Always cite which document and section your answer comes from.

{conversation_history}
Context:
{context}

Question: {question}

Provide a clear, well-structured answer with source citations. If you suggest follow-up questions, format them as a JSON array at the very end of your response after the marker [FOLLOW_UP]:"""

# Sliding window: keep last N message pairs in full, summarize older ones
MEMORY_WINDOW_SIZE = 6  # 3 user + 3 assistant messages


class RAGEngine:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()

    def _bm25_rerank(self, query: str, citations: list[SourceCitation],
                     vector_weight: float = 0.7) -> list[SourceCitation]:
        """Hybrid re-ranking: combine vector similarity with BM25 keyword scores."""
        if not citations:
            return citations
        corpus = [c.chunk_text.lower().split() for c in citations]
        bm25 = BM25Okapi(corpus)
        query_tokens = query.lower().split()
        bm25_scores = bm25.get_scores(query_tokens)

        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
        for i, citation in enumerate(citations):
            bm25_norm = bm25_scores[i] / max_bm25
            citation.relevance_score = (
                vector_weight * citation.relevance_score
                + (1 - vector_weight) * bm25_norm
            )

        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        return citations

    async def _build_conversation_history(
        self, conversation_id: UUID | None, db: AsyncSession, model: str | None = None
    ) -> str:
        """Build conversation context using sliding window + summarization."""
        if not conversation_id:
            return ""

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()

        if not messages:
            return ""

        # If few messages, include all
        if len(messages) <= MEMORY_WINDOW_SIZE:
            lines = [f"{m.role.capitalize()}: {m.content}" for m in messages]
            return "Conversation so far:\n" + "\n".join(lines) + "\n\n"

        # Summarize older messages, keep recent window in full
        older = messages[:-MEMORY_WINDOW_SIZE]
        recent = messages[-MEMORY_WINDOW_SIZE:]

        older_text = "\n".join(f"{m.role.capitalize()}: {m.content}" for m in older)
        try:
            summary = await self.llm_service.summarize(older_text, model)
            summary_section = f"Summary of earlier conversation:\n{summary}\n\n"
        except Exception:
            # Fallback: truncate older messages
            summary_section = f"Earlier context (truncated):\n{older_text[:500]}\n\n"

        recent_lines = [f"{m.role.capitalize()}: {m.content}" for m in recent]
        recent_section = "Recent messages:\n" + "\n".join(recent_lines) + "\n\n"

        return summary_section + recent_section

    async def retrieve_context(self, query: str, user_id: UUID,
                               db: AsyncSession, document_ids: list[UUID] | None = None,
                               top_k: int | None = None) -> list[SourceCitation]:
        top_k = top_k or settings.top_k
        stmt = select(Document).where(
            Document.owner_id == user_id,
            Document.status == "ready",
        )
        if document_ids:
            stmt = stmt.where(Document.id.in_(document_ids))
        result = await db.execute(stmt)
        documents = result.scalars().all()

        if not documents:
            return []

        all_citations = []
        for doc in documents:
            if not doc.collection_id:
                continue
            try:
                results = await self.embedding_service.query_similar(
                    doc.collection_id, query, top_k=top_k
                )
                if results and results.get("documents") and results["documents"][0]:
                    for i, chunk_text in enumerate(results["documents"][0]):
                        meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                        distance = results["distances"][0][i] if results.get("distances") else 0
                        all_citations.append(SourceCitation(
                            document_id=str(doc.id),
                            document_name=doc.filename,
                            page_number=meta.get("page_number"),
                            chunk_text=chunk_text,
                            relevance_score=1 - distance,
                        ))
            except Exception:
                continue

        all_citations = self._bm25_rerank(query, all_citations)
        return all_citations[:top_k]

    def _build_prompt(self, query: str, citations: list[SourceCitation],
                      conversation_history: str = "") -> str:
        context_parts = []
        for i, c in enumerate(citations, 1):
            page_info = f" (Page {c.page_number})" if c.page_number else ""
            context_parts.append(f"[{i}] {c.document_name}{page_info}:\n{c.chunk_text}")
        context = "\n\n".join(context_parts)
        return SYSTEM_PROMPT.format(
            context=context, question=query,
            conversation_history=conversation_history,
        )

    async def answer(
        self, query: str, user_id: UUID, db: AsyncSession,
        conversation_id: UUID | None = None,
        document_ids: list[UUID] | None = None,
        model: str | None = None, temperature: float | None = None,
        top_k: int | None = None,
    ) -> tuple[str, list[SourceCitation], list[str], float, int | None, int | None]:
        """Returns (answer, citations, follow_ups, latency_ms, input_tokens, output_tokens)."""
        start = time.perf_counter()

        # Build conversation memory
        conv_history = await self._build_conversation_history(conversation_id, db, model)

        # Retrieve and rank
        citations = await self.retrieve_context(query, user_id, db, document_ids, top_k)
        prompt = self._build_prompt(query, citations, conv_history)

        # Generate
        llm_resp = await self.llm_service.generate(prompt, model, temperature)

        # Parse follow-up suggestions
        raw_answer = llm_resp.text
        follow_ups = []
        if "[FOLLOW_UP]:" in raw_answer:
            parts = raw_answer.split("[FOLLOW_UP]:")
            raw_answer = parts[0].strip()
            try:
                follow_ups = json.loads(parts[1].strip())
            except (json.JSONDecodeError, IndexError):
                pass

        latency_ms = (time.perf_counter() - start) * 1000
        return raw_answer, citations, follow_ups, latency_ms, llm_resp.input_tokens, llm_resp.output_tokens
