import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "secret123",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["role"] == "user"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "secret123"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "password": "pass123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com", "password": "pass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com", "password": "correct",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com", "password": "incorrect",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "ghost@example.com", "password": "nope",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "refresh@example.com", "password": "pass123",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "refresh@example.com", "password": "pass123",
    })
    refresh = login_resp.json()["refresh_token"]
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh,
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, auth_headers):
    resp = await client.post("/api/v1/auth/api-keys", json={"name": "test-key"},
                             headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-key"
    assert "key" in data
    assert data["key"].startswith("dm_")


@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient, auth_headers):
    await client.post("/api/v1/auth/api-keys", json={"name": "k1"}, headers=auth_headers)
    await client.post("/api/v1/auth/api-keys", json={"name": "k2"}, headers=auth_headers)
    resp = await client.get("/api/v1/auth/api-keys", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2
