import pytest
from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient, auth_headers: dict[str, str]):
    login = await client.post(
        "/api/v1/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    old_refresh = login.json()["refresh_token"]

    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refresh_resp.status_code == 200
    new_refresh = refresh_resp.json()["refresh_token"]
    assert new_refresh != old_refresh


@pytest.mark.asyncio
async def test_reused_refresh_token_is_rejected_and_revokes_session(
    client: AsyncClient, auth_headers: dict[str, str]
):
    login = await client.post(
        "/api/v1/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    old_refresh = login.json()["refresh_token"]

    first_use = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first_use.status_code == 200
    rotated_refresh = first_use.json()["refresh_token"]

    # Replaying the already-rotated token signals theft: it must be
    # rejected, and the token issued from that reuse must also be revoked.
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401

    followup = await client.post("/api/v1/auth/refresh", json={"refresh_token": rotated_refresh})
    assert followup.status_code == 401


@pytest.mark.asyncio
async def test_invalid_login_credentials_rejected(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.post(
        "/api/v1/auth/login", data={"username": ADMIN_EMAIL, "password": "wrong-password"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_email_registration_rejected(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": ADMIN_EMAIL, "password": "another-password", "full_name": "Someone Else"},
        headers=auth_headers,
    )
    assert resp.status_code == 409
