import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import MaintenanceStatus, ReportCategory


class DamageReportBase(BaseModel):
    title: str
    description: str
    category: ReportCategory = ReportCategory.DAMAGE
    location_detail: str | None = None
    room_id: uuid.UUID | None = None
    resident_id: uuid.UUID | None = None


class DamageReportCreate(DamageReportBase):
    pass


class DamageReportUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_to_id: uuid.UUID | None = None
    resolution_notes: str | None = None


class DamageReportStatusUpdate(BaseModel):
    status: MaintenanceStatus
    note: str | None = None


class DamageReportRead(DamageReportBase):
    id: uuid.UUID
    status: MaintenanceStatus
    reported_by_id: uuid.UUID | None = None
    assigned_to_id: uuid.UUID | None = None
    photo_urls: list[str] = []
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DamageReportStatusHistoryRead(BaseModel):
    id: uuid.UUID
    from_status: MaintenanceStatus | None = None
    to_status: MaintenanceStatus
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
