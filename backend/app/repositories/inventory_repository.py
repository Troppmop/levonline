from sqlalchemy import select

from app.models.enums import InventoryCategory, InventoryLocation
from app.models.inventory import InventoryItem, InventoryTransaction
from app.repositories.base import BaseRepository


class InventoryItemRepository(BaseRepository[InventoryItem]):
    model = InventoryItem

    async def list_filtered(
        self,
        location: InventoryLocation | None = None,
        category: InventoryCategory | None = None,
        low_stock_only: bool = False,
        offset: int = 0,
        limit: int = 200,
    ):
        stmt = select(InventoryItem)
        if location is not None:
            stmt = stmt.where(InventoryItem.location == location)
        if category is not None:
            stmt = stmt.where(InventoryItem.category == category)
        if low_stock_only:
            stmt = stmt.where(InventoryItem.quantity <= InventoryItem.low_stock_threshold)
        stmt = stmt.order_by(InventoryItem.location, InventoryItem.name).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_low_stock(self):
        stmt = select(InventoryItem).where(InventoryItem.quantity <= InventoryItem.low_stock_threshold)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class InventoryTransactionRepository(BaseRepository[InventoryTransaction]):
    model = InventoryTransaction

    async def list_for_item(self, item_id, offset: int = 0, limit: int = 100):
        stmt = (
            select(InventoryTransaction)
            .where(InventoryTransaction.item_id == item_id)
            .order_by(InventoryTransaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
