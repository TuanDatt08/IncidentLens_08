import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_v1_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_template_routes_are_not_public(client):
    assert (await client.post("/api/v1/chat", json={"message": "hello"})).status_code == 404
    assert (await client.get("/api/v1/status")).status_code == 404
