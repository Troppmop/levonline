import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_adjust_inventory_item(client: AsyncClient, auth_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/v1/inventory",
        json={
            "name": "Canned Tuna",
            "category": "non_perishable",
            "location": "floor_1_kitchen",
            "unit": "cans",
            "low_stock_threshold": 5,
            "quantity": 10,
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    item = create_resp.json()
    assert item["quantity"] == 10
    assert item["is_low_stock"] is False

    adjust_resp = await client.post(
        f"/api/v1/inventory/{item['id']}/adjust",
        json={"change_quantity": -8, "reason": "consumption"},
        headers=auth_headers,
    )
    assert adjust_resp.status_code == 200
    assert adjust_resp.json()["quantity"] == 2
    assert adjust_resp.json()["is_low_stock"] is True


@pytest.mark.asyncio
async def test_adjust_rejects_negative_stock(client: AsyncClient, auth_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/v1/inventory",
        json={
            "name": "Paper Towels",
            "category": "paper_goods",
            "location": "basement",
            "quantity": 3,
        },
        headers=auth_headers,
    )
    item_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/inventory/{item_id}/adjust",
        json={"change_quantity": -5, "reason": "consumption"},
        headers=auth_headers,
    )
    assert resp.status_code == 422

    # Rejected adjustment must not have partially applied — quantity is unchanged.
    get_resp = await client.get(f"/api/v1/inventory/{item_id}", headers=auth_headers)
    assert get_resp.json()["quantity"] == 3


@pytest.mark.asyncio
async def test_low_stock_filter(client: AsyncClient, auth_headers: dict[str, str]):
    await client.post(
        "/api/v1/inventory",
        json={
            "name": "Milk",
            "category": "perishable",
            "location": "floor_2_kitchen",
            "quantity": 1,
            "low_stock_threshold": 2,
        },
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/inventory",
        json={
            "name": "Rice",
            "category": "non_perishable",
            "location": "floor_2_kitchen",
            "quantity": 50,
            "low_stock_threshold": 5,
        },
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/inventory/low-stock", headers=auth_headers)
    assert resp.status_code == 200
    names = [i["name"] for i in resp.json()]
    assert "Milk" in names
    assert "Rice" not in names
