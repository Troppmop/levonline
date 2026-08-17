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


@pytest.mark.asyncio
async def test_update_own_profile(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.patch(
        "/api/v1/auth/me", json={"full_name": "New Name"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "New Name"
    assert resp.json()["email"] == ADMIN_EMAIL  # untouched field stays as-is


@pytest.mark.asyncio
async def test_update_profile_email_conflict(client: AsyncClient, auth_headers: dict[str, str], make_login):
    from app.models.enums import UserRole

    await make_login("other@example.com", "password123", UserRole.STAFF)

    resp = await client.patch(
        "/api/v1/auth/me", json={"email": "other@example.com"}, headers=auth_headers
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_change_password_requires_current_password(client: AsyncClient, auth_headers: dict[str, str]):
    wrong = await client.post(
        "/api/v1/auth/me/change-password",
        json={"current_password": "not-the-real-password", "new_password": "brand-new-password"},
        headers=auth_headers,
    )
    assert wrong.status_code == 401

    right = await client.post(
        "/api/v1/auth/me/change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "brand-new-password"},
        headers=auth_headers,
    )
    assert right.status_code == 204

    # Old password no longer works; new one does.
    old_login = await client.post(
        "/api/v1/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login", data={"username": ADMIN_EMAIL, "password": "brand-new-password"}
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_revokes_other_sessions(client: AsyncClient, auth_headers: dict[str, str]):
    # A second, independent login for the same user...
    second_login = await client.post(
        "/api/v1/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    second_refresh = second_login.json()["refresh_token"]

    # ...changing the password (via the first session) must kill it.
    await client.post(
        "/api/v1/auth/me/change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "another-new-password"},
        headers=auth_headers,
    )

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": second_refresh})
    assert resp.status_code == 401
