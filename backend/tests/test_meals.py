import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_hosting_record_and_summary(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.post(
        "/api/v1/meals",
        json={
            "host_family_name": "The Cohens",
            "guest_name": "Yossi Levi",
            "meal_date": "2026-08-15",
            "meal_type": "shabbat",
            "guest_count": 2,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    summary_resp = await client.get("/api/v1/meals/summary", headers=auth_headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert len(summary) == 1
    assert summary[0]["host_family_name"] == "The Cohens"
    assert summary[0]["total_meals_hosted"] == 1
    assert summary[0]["total_guests_hosted"] == 2


@pytest.mark.asyncio
async def test_hosting_record_requires_guest_identity(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.post(
        "/api/v1/meals",
        json={"host_family_name": "The Cohens", "meal_date": "2026-08-15"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
