import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_damage_report_lifecycle(client: AsyncClient, auth_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/v1/maintenance/reports",
        json={"title": "Leaky faucet", "description": "Kitchen sink drips constantly"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    report = create_resp.json()
    assert report["status"] == "new"
    report_id = report["id"]

    history_resp = await client.get(f"/api/v1/maintenance/reports/{report_id}/history", headers=auth_headers)
    assert len(history_resp.json()) == 1
    assert history_resp.json()[0]["to_status"] == "new"

    ack_resp = await client.patch(
        f"/api/v1/maintenance/reports/{report_id}/status",
        json={"status": "acknowledged"},
        headers=auth_headers,
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"

    close_resp = await client.patch(
        f"/api/v1/maintenance/reports/{report_id}/status",
        json={"status": "closed", "note": "Fixed the washer"},
        headers=auth_headers,
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"

    history_resp = await client.get(f"/api/v1/maintenance/reports/{report_id}/history", headers=auth_headers)
    assert len(history_resp.json()) == 3


@pytest.mark.asyncio
async def test_invalid_status_transition_rejected(client: AsyncClient, auth_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/v1/maintenance/reports",
        json={"title": "Broken window", "description": "Cracked glass in room 201"},
        headers=auth_headers,
    )
    report_id = create_resp.json()["id"]

    # New -> Closed is not a valid direct transition (must be acknowledged
    # or in-progress first).
    resp = await client.patch(
        f"/api/v1/maintenance/reports/{report_id}/status",
        json={"status": "closed"},
        headers=auth_headers,
    )
    assert resp.status_code == 422

    get_resp = await client.get(f"/api/v1/maintenance/reports/{report_id}", headers=auth_headers)
    assert get_resp.json()["status"] == "new"
