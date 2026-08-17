import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship

from app.models.base import TimestampMixin, UUIDPrimaryKey
from app.models.enums import MaintenanceStatus, ReportCategory

if TYPE_CHECKING:
    from app.models.resident import Resident


class DamageReport(UUIDPrimaryKey, TimestampMixin, table=True):
    """Despite the table/class name (kept for migration continuity), this
    covers both damage reports and cleaning requests — they share the same
    New -> Acknowledged -> In Progress -> Closed pipeline and only differ by
    `category`, so a parallel model/table would just be duplication."""

    __tablename__ = "damage_reports"

    title: str
    description: str
    category: ReportCategory = Field(default=ReportCategory.DAMAGE, index=True)
    status: MaintenanceStatus = Field(default=MaintenanceStatus.NEW, index=True)

    room_id: uuid.UUID | None = Field(default=None, foreign_key="rooms.id", index=True)
    resident_id: uuid.UUID | None = Field(default=None, foreign_key="residents.id", index=True)
    reported_by_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    assigned_to_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")

    photo_urls: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    resolution_notes: str | None = None

    resident: Optional["Resident"] = Relationship(back_populates="damage_reports")
    status_history: list["DamageReportStatusHistory"] = Relationship(
        back_populates="damage_report",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class DamageReportStatusHistory(UUIDPrimaryKey, TimestampMixin, table=True):
    """Tracks every status transition (New -> Acknowledged -> In Progress ->
    Closed) so there's a full audit trail of a repair's lifecycle."""

    __tablename__ = "damage_report_status_history"

    damage_report_id: uuid.UUID = Field(foreign_key="damage_reports.id", index=True, nullable=False)
    from_status: MaintenanceStatus | None = None
    to_status: MaintenanceStatus
    changed_by_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    note: str | None = None

    damage_report: DamageReport | None = Relationship(back_populates="status_history")
