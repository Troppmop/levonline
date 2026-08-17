import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep, StaffOrAdmin
from app.api.pagination import PaginationDep
from app.models.enums import InventoryCategory, InventoryLocation
from app.schemas.inventory import (
    InventoryAdjustment,
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryItemRead])
async def list_items(
    session: SessionDep,
    _: CurrentUser,
    pagination: PaginationDep,
    location: InventoryLocation | None = None,
    category: InventoryCategory | None = None,
    low_stock_only: bool = Query(False),
):
    return await InventoryService(session).list_filtered(
        location=location,
        category=category,
        low_stock_only=low_stock_only,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.get("/low-stock", response_model=list[InventoryItemRead])
async def low_stock(session: SessionDep, _: CurrentUser):
    return await InventoryService(session).low_stock_items()


@router.post("", response_model=InventoryItemRead, status_code=201)
async def create_item(session: SessionDep, _: StaffOrAdmin, payload: InventoryItemCreate):
    return await InventoryService(session).create(payload)


@router.get("/{item_id}", response_model=InventoryItemRead)
async def get_item(session: SessionDep, _: CurrentUser, item_id: uuid.UUID):
    return await InventoryService(session).get(item_id)


@router.patch("/{item_id}", response_model=InventoryItemRead)
async def update_item(session: SessionDep, _: StaffOrAdmin, item_id: uuid.UUID, payload: InventoryItemUpdate):
    return await InventoryService(session).update(item_id, payload)


@router.post("/{item_id}/adjust", response_model=InventoryItemRead)
async def adjust_item(session: SessionDep, _: StaffOrAdmin, item_id: uuid.UUID, payload: InventoryAdjustment):
    return await InventoryService(session).adjust_quantity(item_id, payload.change_quantity, payload.reason)


@router.delete("/{item_id}", status_code=204)
async def delete_item(session: SessionDep, _: StaffOrAdmin, item_id: uuid.UUID):
    await InventoryService(session).delete(item_id)
