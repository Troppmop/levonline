import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import InventoryCategory, InventoryLocation
from app.models.inventory import InventoryItem, InventoryTransaction
from app.repositories.inventory_repository import InventoryItemRepository, InventoryTransactionRepository
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate


class InventoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.items = InventoryItemRepository(session)
        self.transactions = InventoryTransactionRepository(session)

    async def get(self, item_id: uuid.UUID) -> InventoryItem:
        item = await self.items.get(item_id)
        if not item:
            raise NotFoundError("Inventory item not found")
        return item

    async def list_filtered(
        self,
        location: InventoryLocation | None = None,
        category: InventoryCategory | None = None,
        low_stock_only: bool = False,
        offset: int = 0,
        limit: int = 100,
    ):
        return await self.items.list_filtered(
            location=location,
            category=category,
            low_stock_only=low_stock_only,
            offset=offset,
            limit=limit,
        )

    async def create(self, data: InventoryItemCreate) -> InventoryItem:
        item = InventoryItem(**data.model_dump())
        item = await self.items.create(item)
        if item.quantity:
            await self._record_transaction(item.id, item.quantity, "initial_stock")
        return item

    async def update(self, item_id: uuid.UUID, data: InventoryItemUpdate) -> InventoryItem:
        item = await self.items.get(item_id)
        if not item:
            raise NotFoundError("Inventory item not found")
        changes = data.model_dump(exclude_unset=True)
        return await self.items.update(item, changes)

    async def adjust_quantity(self, item_id: uuid.UUID, change_quantity: float, reason: str) -> InventoryItem:
        item = await self.items.get(item_id)
        if not item:
            raise NotFoundError("Inventory item not found")

        new_quantity = item.quantity + change_quantity
        if new_quantity < 0:
            raise ValidationError("Adjustment would result in negative stock")

        update_data = {"quantity": new_quantity}
        if change_quantity > 0:
            update_data["last_restocked_at"] = date.today()
        item = await self.items.update(item, update_data)

        await self._record_transaction(item_id, change_quantity, reason)
        return item

    async def low_stock_items(self):
        return await self.items.list_low_stock()

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.items.get(item_id)
        if not item:
            raise NotFoundError("Inventory item not found")
        await self.items.delete(item)

    async def _record_transaction(self, item_id: uuid.UUID, change_quantity: float, reason: str) -> None:
        transaction = InventoryTransaction(item_id=item_id, change_quantity=change_quantity, reason=reason)
        await self.transactions.create(transaction)
