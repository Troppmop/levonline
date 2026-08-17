import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKey
from app.models.enums import AnnouncementCategory


class Announcement(UUIDPrimaryKey, TimestampMixin, table=True):
    """A posted item on the resident daily feed: house announcements,
    Tefillah time postings, or emergency updates.

    Audience targeting: audience_av_bayit_id null means visible to every
    resident; set means visible only to residents assigned to that
    Av/Eim Bayit account (group-specific communication).
    """

    __tablename__ = "announcements"

    title: str
    body: str
    category: AnnouncementCategory = Field(default=AnnouncementCategory.GENERAL, index=True)
    pinned: bool = Field(default=False, index=True)
    # Free-text event details for time-sensitive posts, e.g. location
    # "Main Dining Room" and time "Tonight @ 20:00" — plain strings rather
    # than a structured datetime since these are often relative/informal.
    event_location: str | None = None
    event_time: str | None = None

    audience_av_bayit_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    created_by_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    expires_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
