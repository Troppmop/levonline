import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_vapid_public_key_endpoint_is_public(client: AsyncClient):
    resp = await client.get("/api/v1/push/vapid-public-key")
    assert resp.status_code == 200
    assert "public_key" in resp.json()


@pytest.mark.asyncio
async def test_subscribe_then_unsubscribe(client: AsyncClient, auth_headers: dict[str, str]):
    payload = {
        "endpoint": "https://push.example.com/abc123",
        "keys": {"p256dh": "test-p256dh-key", "auth": "test-auth-key"},
    }
    sub_resp = await client.post("/api/v1/push/subscribe", json=payload, headers=auth_headers)
    assert sub_resp.status_code == 201
    body = sub_resp.json()
    assert body["endpoint"] == payload["endpoint"]

    # Re-subscribing the same endpoint updates in place rather than erroring.
    sub_resp2 = await client.post("/api/v1/push/subscribe", json=payload, headers=auth_headers)
    assert sub_resp2.status_code == 201
    assert sub_resp2.json()["id"] == body["id"]

    unsub_resp = await client.request(
        "DELETE", "/api/v1/push/unsubscribe", json={"endpoint": payload["endpoint"]}, headers=auth_headers
    )
    assert unsub_resp.status_code == 204


@pytest.mark.asyncio
async def test_subscribe_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/push/subscribe",
        json={"endpoint": "https://push.example.com/x", "keys": {"p256dh": "a", "auth": "b"}},
    )
    assert resp.status_code == 401
