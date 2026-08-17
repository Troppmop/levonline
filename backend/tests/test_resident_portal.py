import pytest
from httpx import AsyncClient

from app.models.enums import UserRole


@pytest.mark.asyncio
async def test_resident_sees_only_own_profile(client: AsyncClient, auth_headers, make_login):
    create_resp = await client.post(
        "/api/v1/residents", json={"first_name": "Yossi", "last_name": "Cohen"}, headers=auth_headers
    )
    resident_id = create_resp.json()["id"]

    other_resp = await client.post(
        "/api/v1/residents", json={"first_name": "Other", "last_name": "Resident"}, headers=auth_headers
    )
    other_id = other_resp.json()["id"]

    resident_headers = await make_login(
        "yossi@example.com", "password123", UserRole.RESIDENT, resident_id=resident_id
    )

    me = await client.get("/api/v1/residents/me", headers=resident_headers)
    assert me.status_code == 200
    assert me.json()["id"] == resident_id

    # Can't browse the roster or another resident's profile.
    assert (await client.get("/api/v1/residents", headers=resident_headers)).status_code == 403
    assert (
        await client.get(f"/api/v1/residents/{other_id}", headers=resident_headers)
    ).status_code == 403


@pytest.mark.asyncio
async def test_resident_can_toggle_own_status_but_not_others(
    client: AsyncClient, auth_headers, make_login
):
    create_resp = await client.post(
        "/api/v1/residents", json={"first_name": "Dovid", "last_name": "Levi"}, headers=auth_headers
    )
    resident_id = create_resp.json()["id"]
    resident_headers = await make_login(
        "dovid@example.com", "password123", UserRole.RESIDENT, resident_id=resident_id
    )

    resp = await client.patch(
        "/api/v1/residents/me/status", json={"status": "away"}, headers=resident_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "away"

    # The staff-directed endpoint targeting an arbitrary id is off-limits.
    forbidden = await client.patch(
        f"/api/v1/residents/{resident_id}/status", json={"status": "home"}, headers=resident_headers
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_resident_files_report_auto_scoped_to_self(client: AsyncClient, auth_headers, make_login):
    create_resp = await client.post(
        "/api/v1/residents", json={"first_name": "Test", "last_name": "Resident"}, headers=auth_headers
    )
    resident_id = create_resp.json()["id"]
    resident_headers = await make_login(
        "test-resident@example.com", "password123", UserRole.RESIDENT, resident_id=resident_id
    )

    # Attempt to file it under someone else's resident_id — must be ignored.
    report_resp = await client.post(
        "/api/v1/maintenance/reports",
        json={
            "title": "Clogged drain",
            "description": "Bathroom sink won't drain",
            "category": "cleaning",
            "resident_id": "00000000-0000-0000-0000-000000000099",
        },
        headers=resident_headers,
    )
    assert report_resp.status_code == 201
    assert report_resp.json()["resident_id"] == resident_id
    assert report_resp.json()["category"] == "cleaning"

    # Shows up in their own filtered list.
    list_resp = await client.get("/api/v1/maintenance/reports", headers=resident_headers)
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_meal_invitation_accept_flow(client: AsyncClient, auth_headers, make_login):
    resident_resp = await client.post(
        "/api/v1/residents", json={"first_name": "Guest", "last_name": "Soldier"}, headers=auth_headers
    )
    resident_id = resident_resp.json()["id"]
    resident_headers = await make_login(
        "guest-soldier@example.com", "password123", UserRole.RESIDENT, resident_id=resident_id
    )
    host_headers = await make_login("host@example.com", "password123", UserRole.AV_BAYIT)

    invite_resp = await client.post(
        "/api/v1/meals/invitations",
        json={
            "host_family_name": "The Levis",
            "resident_id": resident_id,
            "meal_date": "2026-08-22",
            "meal_type": "shabbat",
        },
        headers=host_headers,
    )
    assert invite_resp.status_code == 201
    invitation_id = invite_resp.json()["id"]
    assert invite_resp.json()["status"] == "pending"

    mine = await client.get("/api/v1/meals/invitations/mine", headers=resident_headers)
    assert len(mine.json()) == 1

    accept_resp = await client.patch(
        f"/api/v1/meals/invitations/{invitation_id}/respond",
        json={"status": "accepted"},
        headers=resident_headers,
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "accepted"

    # Responding twice is rejected.
    again = await client.patch(
        f"/api/v1/meals/invitations/{invitation_id}/respond",
        json={"status": "declined"},
        headers=resident_headers,
    )
    assert again.status_code == 422


@pytest.mark.asyncio
async def test_announcements_scoped_by_audience(client: AsyncClient, auth_headers, make_login):
    resident_resp = await client.post(
        "/api/v1/residents", json={"first_name": "A", "last_name": "B"}, headers=auth_headers
    )
    resident_id = resident_resp.json()["id"]

    host_headers = await make_login("family@example.com", "password123", UserRole.AV_BAYIT)
    # Get the host's user id from /auth/me to assign the resident to them.
    me_resp = await client.get("/api/v1/auth/me", headers=host_headers)
    host_id = me_resp.json()["id"]

    await client.patch(
        f"/api/v1/residents/{resident_id}",
        json={"assigned_av_bayit_id": host_id},
        headers=auth_headers,
    )
    resident_headers = await make_login(
        "assigned-resident@example.com", "password123", UserRole.RESIDENT, resident_id=resident_id
    )

    await client.post(
        "/api/v1/announcements",
        json={"title": "House meeting", "body": "Tonight at 8", "category": "general"},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/announcements",
        json={"title": "Our Shabbat plans", "body": "Come at 6", "category": "general"},
        headers=host_headers,
    )

    resp = await client.get("/api/v1/announcements", headers=resident_headers)
    assert resp.status_code == 200
    titles = {a["title"] for a in resp.json()}
    assert titles == {"House meeting", "Our Shabbat plans"}
