from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.resident import Resident, ResidentActivityLog
from app.repositories.base import BaseRepository


class ResidentRepository(BaseRepository[Resident]):
    model = Resident

    async def get_with_room(self, id):
        stmt = select(Resident).options(selectinload(Resident.room)).where(Resident.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_with_room(
        self,
        offset: int = 0,
        limit: int = 200,
        is_active: bool | None = True,
        assigned_av_bayit_id=None,
    ):
        stmt = select(Resident).options(selectinload(Resident.room))
        if is_active is not None:
            stmt = stmt.where(Resident.is_active == is_active)
        if assigned_av_bayit_id is not None:
            stmt = stmt.where(Resident.assigned_av_bayit_id == assigned_av_bayit_id)
        stmt = stmt.order_by(Resident.last_name, Resident.first_name).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class ResidentActivityLogRepository(BaseRepository[ResidentActivityLog]):
    model = ResidentActivityLog

    async def list_for_resident(self, resident_id, offset: int = 0, limit: int = 100):
        stmt = (
            select(ResidentActivityLog)
            .where(ResidentActivityLog.resident_id == resident_id)
            .order_by(ResidentActivityLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
