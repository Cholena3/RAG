import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient, auth_headers, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello world, this is a test document.")

    with patch("app.routers.documents.ingest_document") as mock_ingest:
        mock_ingest.delay = MagicMock()
        with open(test_file, "rb") as f:
            resp = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.txt", f, "text/plain")},
                headers=auth_headers,
            )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "test.txt"
    assert data["file_type"] == "txt"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_unsupported_type(client: AsyncClient, auth_headers, tmp_path):
    test_file = tmp_path / "test.exe"
    test_file.write_bytes(b"\x00\x01\x02")

    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.exe", open(test_file, "rb"), "application/octet-stream")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "unsupported" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/documents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["documents"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_documents_with_upload(client: AsyncClient, auth_headers, tmp_path):
    test_file = tmp_path / "doc.txt"
    test_file.write_text("content")

    with patch("app.routers.documents.ingest_document") as mock_ingest:
        mock_ingest.delay = MagicMock()
        with open(test_file, "rb") as f:
            await client.post(
                "/api/v1/documents/upload",
                files={"file": ("doc.txt", f, "text/plain")},
                headers=auth_headers,
            )

    resp = await client.get("/api/v1/documents", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_document(client: AsyncClient, auth_headers, tmp_path):
    test_file = tmp_path / "get.txt"
    test_file.write_text("get me")

    with patch("app.routers.documents.ingest_document") as mock_ingest:
        mock_ingest.delay = MagicMock()
        with open(test_file, "rb") as f:
            upload_resp = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("get.txt", f, "text/plain")},
                headers=auth_headers,
            )
    doc_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["filename"] == "get.txt"


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient, auth_headers):
    resp = await client.get(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, auth_headers, tmp_path):
    test_file = tmp_path / "del.txt"
    test_file.write_text("delete me")

    with patch("app.routers.documents.ingest_document") as mock_ingest:
        mock_ingest.delay = MagicMock()
        with open(test_file, "rb") as f:
            upload_resp = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("del.txt", f, "text/plain")},
                headers=auth_headers,
            )
    doc_id = upload_resp.json()["id"]

    with patch("app.routers.documents.EmbeddingService"):
        resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_update_document_tags(client: AsyncClient, auth_headers, tmp_path):
    test_file = tmp_path / "tag.txt"
    test_file.write_text("tag me")

    with patch("app.routers.documents.ingest_document") as mock_ingest:
        mock_ingest.delay = MagicMock()
        with open(test_file, "rb") as f:
            upload_resp = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("tag.txt", f, "text/plain")},
                headers=auth_headers,
            )
    doc_id = upload_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/documents/{doc_id}",
        json={"tags": ["important", "review"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["important", "review"]


@pytest.mark.asyncio
async def test_document_status(client: AsyncClient, auth_headers, tmp_path):
    test_file = tmp_path / "status.txt"
    test_file.write_text("check status")

    with patch("app.routers.documents.ingest_document") as mock_ingest:
        mock_ingest.delay = MagicMock()
        with open(test_file, "rb") as f:
            upload_resp = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("status.txt", f, "text/plain")},
                headers=auth_headers,
            )
    doc_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
