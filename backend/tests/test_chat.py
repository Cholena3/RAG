import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from app.schemas.chat import SourceCitation


@pytest.mark.asyncio
async def test_chat_creates_conversation(client: AsyncClient, auth_headers):
    mock_citations = [
        SourceCitation(
            document_id="abc", document_name="test.pdf",
            page_number=1, chunk_text="relevant chunk", relevance_score=0.9,
        )
    ]
    with patch("app.routers.chat.rag_engine") as mock_rag:
        mock_rag.answer = AsyncMock(return_value=(
            "This is the answer.", mock_citations, ["Follow up?"], 150.0
        ))
        resp = await client.post("/api/v1/chat", json={
            "query": "What is this about?",
        }, headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_id" in data
    assert "message_id" in data
    assert data["content"] == "This is the answer."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["document_name"] == "test.pdf"


@pytest.mark.asyncio
async def test_chat_with_existing_conversation(client: AsyncClient, auth_headers):
    with patch("app.routers.chat.rag_engine") as mock_rag:
        mock_rag.answer = AsyncMock(return_value=("Answer 1", [], [], 100.0))
        resp1 = await client.post("/api/v1/chat", json={
            "query": "First question",
        }, headers=auth_headers)

    conv_id = resp1.json()["conversation_id"]

    with patch("app.routers.chat.rag_engine") as mock_rag:
        mock_rag.answer = AsyncMock(return_value=("Answer 2", [], [], 80.0))
        resp2 = await client.post("/api/v1/chat", json={
            "query": "Follow up",
            "conversation_id": conv_id,
        }, headers=auth_headers)

    assert resp2.status_code == 200
    assert resp2.json()["conversation_id"] == conv_id


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, auth_headers):
    with patch("app.routers.chat.rag_engine") as mock_rag:
        mock_rag.answer = AsyncMock(return_value=("Answer", [], [], 50.0))
        await client.post("/api/v1/chat", json={"query": "Q1"}, headers=auth_headers)
        await client.post("/api/v1/chat", json={"query": "Q2"}, headers=auth_headers)

    resp = await client.get("/api/v1/chat/history", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_get_conversation(client: AsyncClient, auth_headers):
    with patch("app.routers.chat.rag_engine") as mock_rag:
        mock_rag.answer = AsyncMock(return_value=("Answer", [], [], 50.0))
        chat_resp = await client.post("/api/v1/chat", json={"query": "Hello"}, headers=auth_headers)

    conv_id = chat_resp.json()["conversation_id"]
    resp = await client.get(f"/api/v1/chat/history/{conv_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == conv_id
    assert len(resp.json()["messages"]) == 2  # user + assistant


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient, auth_headers):
    with patch("app.routers.chat.rag_engine") as mock_rag:
        mock_rag.answer = AsyncMock(return_value=("Answer", [], [], 50.0))
        chat_resp = await client.post("/api/v1/chat", json={"query": "Bye"}, headers=auth_headers)

    conv_id = chat_resp.json()["conversation_id"]
    resp = await client.delete(f"/api/v1/chat/history/{conv_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/chat/history/{conv_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_feedback(client: AsyncClient, auth_headers):
    with patch("app.routers.chat.rag_engine") as mock_rag:
        mock_rag.answer = AsyncMock(return_value=("Good answer", [], [], 50.0))
        chat_resp = await client.post("/api/v1/chat", json={"query": "Rate me"}, headers=auth_headers)

    msg_id = chat_resp.json()["message_id"]
    resp = await client.post("/api/v1/chat/feedback", json={
        "message_id": msg_id, "feedback": 1,
    }, headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_chat_nonexistent_conversation(client: AsyncClient, auth_headers):
    with patch("app.routers.chat.rag_engine") as mock_rag:
        mock_rag.answer = AsyncMock(return_value=("Answer", [], [], 50.0))
        resp = await client.post("/api/v1/chat", json={
            "query": "Hello",
            "conversation_id": "00000000-0000-0000-0000-000000000000",
        }, headers=auth_headers)
    assert resp.status_code == 404
