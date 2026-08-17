import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep, StaffOrAdmin
from app.api.pagination import PaginationDep
from app.models.enums import UserRole
from app.schemas.announcement import AnnouncementCreate, AnnouncementRead, AnnouncementUpdate
from app.services.announcement_service import AnnouncementService
from app.services.resident_service import ResidentService

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("", response_model=list[AnnouncementRead])
async def list_announcements(session: SessionDep, current_user: CurrentUser, pagination: PaginationDep):
    """Residents see general announcements plus anything targeted at their
    assigned Av/Eim Bayit family; Av/Eim Bayit accounts see general plus
    their own posts; staff/admin see everything."""
    av_bayit_filter: uuid.UUID | None
    if current_user.role == UserRole.RESIDENT:
        resident = await ResidentService(session).get(current_user.resident_id)
        av_bayit_filter = resident.assigned_av_bayit_id or uuid.UUID(int=0)  # never matches -> general-only
    elif current_user.role == UserRole.AV_BAYIT:
        av_bayit_filter = current_user.id
    else:
        av_bayit_filter = None

    return await AnnouncementService(session).list_for_audience(
        av_bayit_id=av_bayit_filter, offset=pagination.offset, limit=pagination.limit
    )


@router.post("", response_model=AnnouncementRead, status_code=201)
async def create_announcement(session: SessionDep, current_user: CurrentUser, payload: AnnouncementCreate):
    """Staff/admin can post to any audience (including emergency/global);
    Av/Eim Bayit accounts may only post to their own assigned residents."""
    if current_user.role == UserRole.AV_BAYIT:
        payload = payload.model_copy(update={"audience_av_bayit_id": current_user.id})
    elif current_user.role == UserRole.RESIDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Residents cannot post announcements"
        )
    return await AnnouncementService(session).create(payload, created_by_id=current_user.id)


@router.patch("/{announcement_id}", response_model=AnnouncementRead)
async def update_announcement(
    session: SessionDep, _: StaffOrAdmin, announcement_id: uuid.UUID, payload: AnnouncementUpdate
):
    return await AnnouncementService(session).update(announcement_id, payload)


@router.delete("/{announcement_id}", status_code=204)
async def delete_announcement(session: SessionDep, _: StaffOrAdmin, announcement_id: uuid.UUID):
    await AnnouncementService(session).delete(announcement_id)
