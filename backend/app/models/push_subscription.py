import uuid

from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKey


class PushSubscription(UUIDPrimaryKey, TimestampMixin, table=True):
    """A browser's Web Push subscription (from the PushManager API),
    one row per browser/device a user has enabled notifications on."""

    __tablename__ = "push_subscriptions"

    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    endpoint: str = Field(unique=True, index=True, nullable=False)
    p256dh: str
    auth: str
