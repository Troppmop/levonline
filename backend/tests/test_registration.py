import pytest
from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL


@pytest.mark.asyncio
async def test_apply_creates_pending_request_visible_to_admin(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/registration/apply",
        json={
            "first_name": "Yossi",
            "last_name": "Cohen",
            "email": "yossi@example.com",
            "phone": "555-1234",
            "password": "password123",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"

    list_resp = await client.get("/api/v1/registration/requests?status=pending", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["email"] == "yossi@example.com"


@pytest.mark.asyncio
async def test_apply_requires_no_auth_but_review_requires_staff(client: AsyncClient):
    resp = await client.post(
        "/api/v1/registration/apply",
        json={"first_name": "A", "last_name": "B", "email": "a@example.com", "password": "password123"},
    )
    assert resp.status_code == 201

    # Listing/approving requires staff or admin.
    assert (await client.get("/api/v1/registration/requests")).status_code == 401


@pytest.mark.asyncio
async def test_duplicate_pending_application_rejected(client: AsyncClient):
    payload = {
        "first_name": "Dup",
        "last_name": "Licate",
        "email": "dup@example.com",
        "password": "password123",
    }
    first = await client.post("/api/v1/registration/apply", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/registration/apply", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_approve_creates_login_resident_can_use(client: AsyncClient, auth_headers):
    apply_resp = await client.post(
        "/api/v1/registration/apply",
        json={
            "first_name": "Approved",
            "last_name": "Soldier",
            "email": "approved@example.com",
            "password": "password123",
        },
    )
    request_id = apply_resp.json()["id"]

    approve_resp = await client.post(
        f"/api/v1/registration/requests/{request_id}/approve", json={}, headers=auth_headers
    )
    assert approve_resp.status_code == 200
    resident = approve_resp.json()
    assert resident["first_name"] == "Approved"
    assert resident["status"] == "home"

    # The applicant can now log in with the password they originally chose.
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "approved@example.com", "password": "password123"},
    )
    assert login.status_code == 200

    # And their own /residents/me matches the approved profile.
    me_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = await client.get("/api/v1/residents/me", headers=me_headers)
    assert me.status_code == 200
    assert me.json()["id"] == resident["id"]

    # A second approval attempt on the same (now-approved) request fails.
    again = await client.post(
        f"/api/v1/registration/requests/{request_id}/approve", json={}, headers=auth_headers
    )
    assert again.status_code == 422


@pytest.mark.asyncio
async def test_reject_leaves_no_login_and_gives_friendly_error(client: AsyncClient, auth_headers):
    apply_resp = await client.post(
        "/api/v1/registration/apply",
        json={
            "first_name": "Rejected",
            "last_name": "Applicant",
            "email": "rejected@example.com",
            "password": "password123",
        },
    )
    request_id = apply_resp.json()["id"]

    reject_resp = await client.post(
        f"/api/v1/registration/requests/{request_id}/reject",
        json={"note": "Not currently affiliated with the program"},
        headers=auth_headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "rejected@example.com", "password": "password123"},
    )
    assert login.status_code == 401
    assert "not approved" in login.json()["detail"]

    # A new application with the same email is allowed after rejection.
    reapply = await client.post(
        "/api/v1/registration/apply",
        json={
            "first_name": "Rejected",
            "last_name": "Applicant",
            "email": "rejected@example.com",
            "password": "a-new-password",
        },
    )
    assert reapply.status_code == 201


@pytest.mark.asyncio
async def test_apply_blocked_if_email_already_has_account(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/registration/apply",
        json={"first_name": "Admin", "last_name": "Again", "email": ADMIN_EMAIL, "password": "password123"},
    )
    assert resp.status_code == 409
