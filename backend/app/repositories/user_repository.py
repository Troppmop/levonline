import uuid

from sqlalchemy import select

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
