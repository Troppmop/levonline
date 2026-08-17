import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import MaintenanceStatus, ReportCategory
from app.models.maintenance import DamageReport, DamageReportStatusHistory
from app.repositories.maintenance_repository import (
    DamageReportRepository,
    DamageReportStatusHistoryRepository,
)
from app.schemas.maintenance import DamageReportCreate, DamageReportUpdate

# Valid forward transitions for the damage report lifecycle. Rejecting
# invalid jumps (e.g. New -> Closed) keeps the status history meaningful.
_ALLOWED_TRANSITIONS: dict[MaintenanceStatus, set[MaintenanceStatus]] = {
    MaintenanceStatus.NEW: {MaintenanceStatus.ACKNOWLEDGED, MaintenanceStatus.IN_PROGRESS},
    MaintenanceStatus.ACKNOWLEDGED: {MaintenanceStatus.IN_PROGRESS, MaintenanceStatus.CLOSED},
    MaintenanceStatus.IN_PROGRESS: {MaintenanceStatus.CLOSED, MaintenanceStatus.ACKNOWLEDGED},
    MaintenanceStatus.CLOSED: set(),
}


class MaintenanceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.reports = DamageReportRepository(session)
        self.history = DamageReportStatusHistoryRepository(session)

    async def get(self, report_id: uuid.UUID) -> DamageReport:
        report = await self.reports.get_with_history(report_id)
        if not report:
            raise NotFoundError("Damage report not found")
        return report

    async def list_filtered(
        self,
        status: MaintenanceStatus | None = None,
        room_id: uuid.UUID | None = None,
        category: ReportCategory | None = None,
        resident_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ):
        return await self.reports.list_filtered(
            status=status,
            room_id=room_id,
            category=category,
            resident_id=resident_id,
            offset=offset,
            limit=limit,
        )

    async def create(self, data: DamageReportCreate, reported_by_id: uuid.UUID | None = None) -> DamageReport:
        report = DamageReport(**data.model_dump(), reported_by_id=reported_by_id)
        report = await self.reports.create(report)
        await self.history.create(
            DamageReportStatusHistory(
                damage_report_id=report.id,
                from_status=None,
                to_status=MaintenanceStatus.NEW,
                changed_by_id=reported_by_id,
            )
        )
        return await self.get(report.id)

    async def update(self, report_id: uuid.UUID, data: DamageReportUpdate) -> DamageReport:
        report = await self.reports.get(report_id)
        if not report:
            raise NotFoundError("Damage report not found")
        changes = data.model_dump(exclude_unset=True)
        await self.reports.update(report, changes)
        return await self.get(report_id)

    async def add_photos(self, report_id: uuid.UUID, photo_urls: list[str]) -> DamageReport:
        report = await self.reports.get(report_id)
        if not report:
            raise NotFoundError("Damage report not found")
        await self.reports.update(report, {"photo_urls": [*report.photo_urls, *photo_urls]})
        return await self.get(report_id)

    async def transition_status(
        self,
        report_id: uuid.UUID,
        new_status: MaintenanceStatus,
        note: str | None,
        actor_id: uuid.UUID | None = None,
    ) -> DamageReport:
        report = await self.reports.get(report_id)
        if not report:
            raise NotFoundError("Damage report not found")

        if new_status != report.status and new_status not in _ALLOWED_TRANSITIONS[report.status]:
            raise ValidationError(f"Cannot transition from {report.status.value} to {new_status.value}")

        old_status = report.status
        await self.reports.update(report, {"status": new_status})
        await self.history.create(
            DamageReportStatusHistory(
                damage_report_id=report_id,
                from_status=old_status,
                to_status=new_status,
                changed_by_id=actor_id,
                note=note,
            )
        )
        return await self.get(report_id)
