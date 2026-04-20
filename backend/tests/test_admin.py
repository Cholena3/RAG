import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_stats(client: AsyncClient, admin_headers):
    resp = await client.get("/api/v1/admin/stats", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert "documents" in data
    assert "conversations" in data
    assert "messages" in data
    assert "feedback" in data


@pytest.mark.asyncio
async def test_admin_stats_forbidden_for_user(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/admin/stats", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_headers):
    resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_list_models(client: AsyncClient, admin_headers):
    with patch("app.routers.admin.llm_service") as mock_llm:
        mock_llm.list_models = AsyncMock(return_value=[
            {"name": "llama3.2", "size": 4_000_000_000},
        ])
        resp = await client.get("/api/v1/admin/models", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_admin_endpoints_require_auth(client: AsyncClient):
    for path in ["/api/v1/admin/stats", "/api/v1/admin/users", "/api/v1/admin/models"]:
        resp = await client.get(path)
        assert resp.status_code == 403
