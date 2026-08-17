import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.announcement import Announcement
from app.repositories.announcement_repository import AnnouncementRepository
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate


class AnnouncementService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.announcements = AnnouncementRepository(session)

    async def get(self, announcement_id: uuid.UUID) -> Announcement:
        announcement = await self.announcements.get(announcement_id)
        if not announcement:
            raise NotFoundError("Announcement not found")
        return announcement

    async def list_for_audience(
        self, av_bayit_id: uuid.UUID | None = None, offset: int = 0, limit: int = 100
    ):
        return await self.announcements.list_for_audience(
            av_bayit_id=av_bayit_id, offset=offset, limit=limit
        )

    async def create(self, data: AnnouncementCreate, created_by_id: uuid.UUID | None = None) -> Announcement:
        announcement = Announcement(**data.model_dump(), created_by_id=created_by_id)
        return await self.announcements.create(announcement)

    async def update(self, announcement_id: uuid.UUID, data: AnnouncementUpdate) -> Announcement:
        announcement = await self.announcements.get(announcement_id)
        if not announcement:
            raise NotFoundError("Announcement not found")
        changes = data.model_dump(exclude_unset=True)
        return await self.announcements.update(announcement, changes)

    async def delete(self, announcement_id: uuid.UUID) -> None:
        announcement = await self.announcements.get(announcement_id)
        if not announcement:
            raise NotFoundError("Announcement not found")
        await self.announcements.delete(announcement)
