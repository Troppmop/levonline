import uuid
from datetime import date

from sqlmodel import Field, Relationship

from app.models.base import TimestampMixin, UUIDPrimaryKey
from app.models.enums import InventoryCategory, InventoryLocation


class InventoryItem(UUIDPrimaryKey, TimestampMixin, table=True):
    __tablename__ = "inventory_items"

    name: str = Field(index=True)
    category: InventoryCategory = Field(index=True)
    location: InventoryLocation = Field(index=True)

    quantity: float = Field(default=0)
    unit: str = Field(default="unit")  # e.g. "cans", "lbs", "rolls"
    low_stock_threshold: float = Field(default=0)

    expiration_date: date | None = None
    last_restocked_at: date | None = None
    notes: str | None = None

    transactions: list["InventoryTransaction"] = Relationship(
        back_populates="item",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.low_stock_threshold


class InventoryTransaction(UUIDPrimaryKey, TimestampMixin, table=True):
    """Append-only log of every quantity change so stock levels are always
    reconstructable/auditable, not just a mutable counter."""

    __tablename__ = "inventory_transactions"

    item_id: uuid.UUID = Field(foreign_key="inventory_items.id", index=True, nullable=False)
    change_quantity: float  # positive = restock, negative = consumption
    reason: str = Field(default="adjustment")
    created_by_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")

    item: InventoryItem | None = Relationship(back_populates="transactions")
