import uuid
from datetime import datetime

from pydantic import BaseModel


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    """Mirrors the shape of `PushSubscription.toJSON()` from the browser's
    Push API, so the frontend can send it through unmodified."""

    endpoint: str
    keys: PushSubscriptionKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class PushSubscriptionRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    endpoint: str
    created_at: datetime

    model_config = {"from_attributes": True}
