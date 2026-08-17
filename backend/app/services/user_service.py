import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)

    async def list_all(self, offset: int = 0, limit: int = 500):
        return await self.users.list(offset=offset, limit=limit)

    async def set_avatar(self, user_id: uuid.UUID, avatar_url: str) -> User:
        user = await self.users.get(user_id)
        if not user:
            raise NotFoundError("User not found")
        return await self.users.update(user, {"avatar_url": avatar_url})
