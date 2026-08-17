import uuid

from sqlalchemy import select

from app.models.enums import UserRole
from app.models.resident import Resident
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_resident_id(self, resident_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.resident_id == resident_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_by_roles(self, *roles: UserRole):
        stmt = select(User).where(User.role.in_(roles), User.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_resident_users_for_audience(self, av_bayit_id: uuid.UUID | None):
        """Resident-role logins to notify about an announcement: everyone,
        if it's general (av_bayit_id is None), or only those assigned to
        the posting Av/Eim Bayit family — mirrors AnnouncementRepository's
        own audience filter so push targeting matches what the feed shows."""
        stmt = (
            select(User)
            .join(Resident, User.resident_id == Resident.id)
            .where(User.role == UserRole.RESIDENT, User.is_active.is_(True))
        )
        if av_bayit_id is not None:
            stmt = stmt.where(Resident.assigned_av_bayit_id == av_bayit_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
