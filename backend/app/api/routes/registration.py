import uuid

from fastapi import APIRouter, Request

from app.api.deps import SessionDep, StaffOrAdmin
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.enums import RegistrationStatus
from app.schemas.registration import (
    RegistrationApprove,
    RegistrationReject,
    RegistrationRequestCreate,
    RegistrationRequestRead,
)
from app.schemas.resident import ResidentRead
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/registration", tags=["registration"])


@router.post("/apply", response_model=RegistrationRequestRead, status_code=201)
@limiter.limit(settings.registration_rate_limit)
async def apply(request: Request, session: SessionDep, payload: RegistrationRequestCreate):
    """Public — no login required. A soldier submits their details here;
    nothing becomes an active account until staff/admin approves it."""
    return await RegistrationService(session).submit(payload)


@router.get("/requests", response_model=list[RegistrationRequestRead])
async def list_requests(session: SessionDep, _: StaffOrAdmin, status: RegistrationStatus | None = None):
    return await RegistrationService(session).list_requests(status)


@router.post("/requests/{request_id}/approve", response_model=ResidentRead)
async def approve_request(
    session: SessionDep, current_user: StaffOrAdmin, request_id: uuid.UUID, payload: RegistrationApprove
):
    return await RegistrationService(session).approve(request_id, current_user.id, payload.room_id)


@router.post("/requests/{request_id}/reject", response_model=RegistrationRequestRead)
async def reject_request(
    session: SessionDep, current_user: StaffOrAdmin, request_id: uuid.UUID, payload: RegistrationReject
):
    return await RegistrationService(session).reject(request_id, current_user.id, payload.note)
