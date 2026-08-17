import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AnnouncementCategory


class AnnouncementBase(BaseModel):
    title: str
    body: str
    category: AnnouncementCategory = AnnouncementCategory.GENERAL
    pinned: bool = False
    audience_av_bayit_id: uuid.UUID | None = None
    expires_at: datetime | None = None


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    category: AnnouncementCategory | None = None
    pinned: bool | None = None
    expires_at: datetime | None = None


class AnnouncementRead(AnnouncementBase):
    id: uuid.UUID
    created_by_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
