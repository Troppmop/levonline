import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import InventoryCategory, InventoryLocation


class InventoryItemBase(BaseModel):
    name: str
    category: InventoryCategory
    location: InventoryLocation
    unit: str = "unit"
    low_stock_threshold: float = 0
    expiration_date: date | None = None
    notes: str | None = None


class InventoryItemCreate(InventoryItemBase):
    quantity: float = 0


class InventoryItemUpdate(BaseModel):
    name: str | None = None
    category: InventoryCategory | None = None
    location: InventoryLocation | None = None
    unit: str | None = None
    low_stock_threshold: float | None = None
    expiration_date: date | None = None
    notes: str | None = None


class InventoryItemRead(InventoryItemBase):
    id: uuid.UUID
    quantity: float
    last_restocked_at: date | None = None
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryAdjustment(BaseModel):
    """Positive change_quantity restocks, negative records consumption."""

    change_quantity: float
    reason: str = "adjustment"


class InventoryTransactionRead(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    change_quantity: float
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}
