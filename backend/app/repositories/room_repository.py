from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.room import Room
from app.repositories.base import BaseRepository


class RoomRepository(BaseRepository[Room]):
    model = Room

    async def list_with_residents(self):
        """Rooms ordered by floor/display_order — the physical layout used
        by the presence tracker, not alphabetical."""
        stmt = (
            select(Room)
            .options(selectinload(Room.residents))
            .order_by(Room.floor, Room.display_order, Room.room_number)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
