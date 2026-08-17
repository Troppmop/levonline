import uuid

from sqlalchemy import select

from app.models.push_subscription import PushSubscription
from app.repositories.base import BaseRepository


class PushSubscriptionRepository(BaseRepository[PushSubscription]):
    model = PushSubscription

    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID):
        stmt = select(PushSubscription).where(PushSubscription.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
