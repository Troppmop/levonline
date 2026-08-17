import asyncio
import json
import logging
import uuid

from pywebpush import WebPushException, webpush
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.push_subscription import PushSubscription
from app.repositories.push_repository import PushSubscriptionRepository
from app.schemas.push import PushSubscriptionCreate

logger = logging.getLogger("app.push")


class PushService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.subscriptions = PushSubscriptionRepository(session)

    async def subscribe(self, user_id: uuid.UUID, payload: PushSubscriptionCreate) -> PushSubscription:
        existing = await self.subscriptions.get_by_endpoint(payload.endpoint)
        if existing:
            return await self.subscriptions.update(
                existing,
                {"user_id": user_id, "p256dh": payload.keys.p256dh, "auth": payload.keys.auth},
            )
        subscription = PushSubscription(
            user_id=user_id,
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
        )
        return await self.subscriptions.create(subscription)

    async def unsubscribe(self, user_id: uuid.UUID, endpoint: str) -> None:
        existing = await self.subscriptions.get_by_endpoint(endpoint)
        # Only remove a subscription that actually belongs to the caller —
        # endpoints aren't guessable, but this closes the gap regardless.
        if existing and existing.user_id == user_id:
            await self.subscriptions.delete(existing)


async def send_notification_to_user(
    session: AsyncSession, user_id: uuid.UUID, title: str, body: str, url: str = "/"
) -> None:
    """Sends a Web Push notification to every subscribed device for a user.
    No-ops (with a log line) if VAPID keys aren't configured, so the
    subscribe/unsubscribe flow and the calling code work in any environment
    without needing real push credentials.

    Subscriptions the push service reports gone (410 Gone / 404 Not Found)
    are deleted here — browsers drop subscriptions silently (uninstall,
    permission revoked, etc.), so this is the only place that finds out.
    """
    if not settings.VAPID_PRIVATE_KEY:
        logger.info("Push not configured (no VAPID_PRIVATE_KEY) — skipping push to %s: %s", user_id, title)
        return

    repo = PushSubscriptionRepository(session)
    subscriptions = await repo.list_for_user(user_id)
    payload = json.dumps({"title": title, "body": body, "url": url})

    for subscription in subscriptions:
        try:
            await asyncio.to_thread(
                webpush,
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIMS_SUB},
            )
        except WebPushException as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in (404, 410):
                await repo.delete(subscription)
            else:
                logger.warning("Push send failed for endpoint %s: %s", subscription.endpoint, exc)
