from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.schemas.push import PushSubscriptionCreate, PushSubscriptionRead, PushUnsubscribeRequest
from app.services.push_service import PushService

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-public-key")
async def get_vapid_public_key() -> dict:
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe", response_model=PushSubscriptionRead, status_code=201)
async def subscribe(session: SessionDep, user: CurrentUser, payload: PushSubscriptionCreate):
    return await PushService(session).subscribe(user.id, payload)


@router.delete("/unsubscribe", status_code=204)
async def unsubscribe(session: SessionDep, user: CurrentUser, payload: PushUnsubscribeRequest):
    await PushService(session).unsubscribe(user.id, payload.endpoint)
