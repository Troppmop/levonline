import base64

import pytest
from httpx import AsyncClient

# 1x1 transparent PNG — small enough to embed inline, valid enough to pass
# the upload's content-type + size checks.
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.mark.asyncio
async def test_upload_own_avatar(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.post(
        "/api/v1/auth/me/avatar",
        files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] is not None

    me_resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_resp.json()["avatar_url"] == resp.json()["avatar_url"]


@pytest.mark.asyncio
async def test_avatar_upload_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/auth/me/avatar", files={"file": ("a.png", _PNG_BYTES, "image/png")})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_list_users_and_set_avatar_for_another(
    client: AsyncClient, auth_headers: dict[str, str], make_login
):
    from app.models.enums import UserRole

    await make_login("staffer@lev.org", "password123", UserRole.STAFF)

    list_resp = await client.get("/api/v1/users", headers=auth_headers)
    assert list_resp.status_code == 200
    staffer = next(u for u in list_resp.json() if u["email"] == "staffer@lev.org")
    assert staffer["avatar_url"] is None

    avatar_resp = await client.post(
        f"/api/v1/users/{staffer['id']}/avatar",
        files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        headers=auth_headers,
    )
    assert avatar_resp.status_code == 200
    assert avatar_resp.json()["avatar_url"] is not None


@pytest.mark.asyncio
async def test_staff_cannot_list_users_or_set_others_avatar(
    client: AsyncClient, auth_headers: dict[str, str], make_login
):
    from app.models.enums import UserRole

    staff_headers = await make_login("staffer2@lev.org", "password123", UserRole.STAFF)

    list_resp = await client.get("/api/v1/users", headers=staff_headers)
    assert list_resp.status_code == 403

    admin_me = await client.get("/api/v1/auth/me", headers=auth_headers)
    admin_id = admin_me.json()["id"]

    avatar_resp = await client.post(
        f"/api/v1/users/{admin_id}/avatar",
        files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        headers=staff_headers,
    )
    assert avatar_resp.status_code == 403
