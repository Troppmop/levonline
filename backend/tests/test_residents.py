import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_fetch_resident(client: AsyncClient, auth_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/v1/residents",
        json={"first_name": "Yossi", "last_name": "Cohen"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    resident_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/residents/{resident_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "home"

    activity_resp = await client.get(f"/api/v1/residents/{resident_id}/activity", headers=auth_headers)
    assert activity_resp.status_code == 200
    assert len(activity_resp.json()) == 1


@pytest.mark.asyncio
async def test_status_toggle_logs_activity(client: AsyncClient, auth_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/v1/residents", json={"first_name": "Dovid", "last_name": "Levi"}, headers=auth_headers
    )
    resident_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/residents/{resident_id}/status", json={"status": "away"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "away"

    activity_resp = await client.get(f"/api/v1/residents/{resident_id}/activity", headers=auth_headers)
    activity_types = [a["activity_type"] for a in activity_resp.json()]
    assert "status_change" in activity_types


@pytest.mark.asyncio
async def test_get_nonexistent_resident_returns_404(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.get(
        "/api/v1/residents/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_residents_require_auth(client: AsyncClient):
    resp = await client.get("/api/v1/residents")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_offboard_archives_resident_and_logs_checklist(
    client: AsyncClient, auth_headers: dict[str, str]
):
    create_resp = await client.post(
        "/api/v1/residents", json={"first_name": "Moshe", "last_name": "Katz"}, headers=auth_headers
    )
    resident_id = create_resp.json()["id"]

    offboard_resp = await client.post(
        f"/api/v1/residents/{resident_id}/offboard",
        json={"key_returned": True, "biometric_cleared": True, "balance_settled": False, "note": "Owes rent"},
        headers=auth_headers,
    )
    assert offboard_resp.status_code == 200
    body = offboard_resp.json()
    assert body["is_active"] is False
    assert body["is_archived"] is True

    activity_resp = await client.get(f"/api/v1/residents/{resident_id}/activity", headers=auth_headers)
    activity_types = [a["activity_type"] for a in activity_resp.json()]
    assert "offboarded" in activity_types

    active_list = await client.get("/api/v1/residents", headers=auth_headers)
    assert resident_id not in [r["id"] for r in active_list.json()]

    archived_list = await client.get("/api/v1/residents?archived=true", headers=auth_headers)
    assert resident_id in [r["id"] for r in archived_list.json()]


@pytest.mark.asyncio
async def test_av_bayit_role_cannot_create_residents(client: AsyncClient, session):
    """Av/Eim Bayit accounts are scoped to meal hosting reports and must not
    be able to edit resident records — building operations are staff-only."""
    from app.core.security import hash_password
    from app.models.enums import UserRole
    from app.models.user import User

    session.add(
        User(
            email="host-family@lev.org",
            hashed_password=hash_password("password123"),
            full_name="Host Family",
            role=UserRole.AV_BAYIT,
        )
    )
    await session.commit()

    login = await client.post(
        "/api/v1/auth/login", data={"username": "host-family@lev.org", "password": "password123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.post(
        "/api/v1/residents", json={"first_name": "Test", "last_name": "Resident"}, headers=headers
    )
    assert resp.status_code == 403

    # But they can still read the presence board (needed to plan hosting).
    read_resp = await client.get("/api/v1/residents", headers=headers)
    assert read_resp.status_code == 200

    # And they can still log a meal hosting record — their actual purpose.
    meal_resp = await client.post(
        "/api/v1/meals",
        json={"host_family_name": "Host Family", "guest_name": "Guest", "meal_date": "2026-08-15"},
        headers=headers,
    )
    assert meal_resp.status_code == 201
