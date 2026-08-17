import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentResident, CurrentUser, NotResident, SessionDep
from app.api.pagination import PaginationDep
from app.schemas.meal import (
    MealHostingRecordCreate,
    MealHostingRecordRead,
    MealHostingSummary,
    MealInvitationCreate,
    MealInvitationRead,
    MealInvitationRespond,
)
from app.services.meal_service import MealService

router = APIRouter(prefix="/meals", tags=["meals"])


@router.get("", response_model=list[MealHostingRecordRead])
async def list_hosting_records(
    session: SessionDep,
    _: CurrentUser,
    pagination: PaginationDep,
    host_family_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    return await MealService(session).list_filtered(
        host_family_name=host_family_name,
        date_from=date_from,
        date_to=date_to,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.post("", response_model=MealHostingRecordRead, status_code=201)
async def create_hosting_record(
    session: SessionDep, current_user: CurrentUser, payload: MealHostingRecordCreate
):
    return await MealService(session).create(payload, host_user_id=current_user.id)


@router.get("/summary", response_model=list[MealHostingSummary])
async def hosting_summary(
    session: SessionDep,
    _: CurrentUser,
    date_from: date | None = None,
    date_to: date | None = None,
):
    return await MealService(session).hosting_summary(date_from=date_from, date_to=date_to)


# --- meal invitations (forward-looking RSVP flow) ---


@router.post("/invitations", response_model=MealInvitationRead, status_code=201)
async def create_invitation(session: SessionDep, current_user: NotResident, payload: MealInvitationCreate):
    """Av/Eim Bayit (or staff helping coordinate) invites a specific
    resident to a meal; the resident accepts/declines from their portal."""
    return await MealService(session).create_invitation(payload, host_user_id=current_user.id)


@router.get("/invitations/sent", response_model=list[MealInvitationRead])
async def list_sent_invitations(session: SessionDep, current_user: NotResident):
    return await MealService(session).list_invitations_for_host(current_user.id)


@router.get("/invitations/mine", response_model=list[MealInvitationRead])
async def list_my_invitations(session: SessionDep, resident: CurrentResident):
    return await MealService(session).list_invitations_for_resident(resident.id)


@router.patch("/invitations/{invitation_id}/respond", response_model=MealInvitationRead)
async def respond_to_invitation(
    session: SessionDep,
    resident: CurrentResident,
    invitation_id: uuid.UUID,
    payload: MealInvitationRespond,
):
    service = MealService(session)
    invitation = await service.get_invitation(invitation_id)
    if invitation.resident_id != resident.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This invitation was not sent to you"
        )
    return await service.respond_to_invitation(invitation_id, payload.status)
