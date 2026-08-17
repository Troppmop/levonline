from sqlalchemy import or_, select

from app.models.announcement import Announcement
from app.repositories.base import BaseRepository


class AnnouncementRepository(BaseRepository[Announcement]):
    model = Announcement

    async def list_for_audience(self, av_bayit_id=None, offset: int = 0, limit: int = 100):
        """Announcements visible to a resident: general (audience is null)
        plus anything targeted at the Av/Eim Bayit family they're assigned
        to. Staff/admin/av_bayit callers pass av_bayit_id=None and get
        everything (their own management view)."""
        stmt = select(Announcement)
        if av_bayit_id is not None:
            stmt = stmt.where(
                or_(
                    Announcement.audience_av_bayit_id.is_(None),
                    Announcement.audience_av_bayit_id == av_bayit_id,
                )
            )
        stmt = (
            stmt.order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
