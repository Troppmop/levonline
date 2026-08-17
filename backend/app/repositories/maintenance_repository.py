from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.enums import MaintenanceStatus, ReportCategory
from app.models.maintenance import DamageReport, DamageReportStatusHistory
from app.repositories.base import BaseRepository


class DamageReportRepository(BaseRepository[DamageReport]):
    model = DamageReport

    async def get_with_history(self, id):
        stmt = (
            select(DamageReport)
            .options(selectinload(DamageReport.status_history))
            .where(DamageReport.id == id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        status: MaintenanceStatus | None = None,
        room_id=None,
        category: ReportCategory | None = None,
        resident_id=None,
        offset: int = 0,
        limit: int = 200,
    ):
        stmt = select(DamageReport)
        if status is not None:
            stmt = stmt.where(DamageReport.status == status)
        if room_id is not None:
            stmt = stmt.where(DamageReport.room_id == room_id)
        if category is not None:
            stmt = stmt.where(DamageReport.category == category)
        if resident_id is not None:
            stmt = stmt.where(DamageReport.resident_id == resident_id)
        stmt = stmt.order_by(DamageReport.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class DamageReportStatusHistoryRepository(BaseRepository[DamageReportStatusHistory]):
    model = DamageReportStatusHistory
