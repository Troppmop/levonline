import uuid

from fastapi import APIRouter

from app.api.deps import CurrentResident, NotResident, SessionDep, StaffOrAdmin
from app.api.pagination import PaginationDep
from app.schemas.resident import (
    ResidentActivityLogRead,
    ResidentCreate,
    ResidentOffboardRequest,
    ResidentRead,
    ResidentStatusUpdate,
    ResidentUpdate,
    RoomWithResidents,
)
from app.services.resident_service import ResidentService

router = APIRouter(prefix="/residents", tags=["residents"])


@router.get("/presence", response_model=list[RoomWithResidents])
async def presence_by_room_layout(session: SessionDep, _: NotResident):
    """Home/Away board grouped and ordered by physical room layout
    (floor + position) rather than alphabetically by resident."""
    rooms = await ResidentService(session).list_by_room_layout()
    return rooms


@router.get("", response_model=list[ResidentRead])
async def list_residents(
    session: SessionDep,
    current_user: NotResident,
    pagination: PaginationDep,
    assigned_to_me: bool = False,
    archived: bool = False,
):
    """assigned_to_me: for Av/Eim Bayit accounts, narrows the roster to
    just the residents assigned to them (used by the hosting portal).
    archived: switches between the Active and Former-Resident tabs."""
    assigned_av_bayit_id = current_user.id if assigned_to_me else None
    return await ResidentService(session).list_residents(
        offset=pagination.offset,
        limit=pagination.limit,
        assigned_av_bayit_id=assigned_av_bayit_id,
        archived=archived,
    )


@router.post("", response_model=ResidentRead, status_code=201)
async def create_resident(session: SessionDep, current_user: StaffOrAdmin, payload: ResidentCreate):
    return await ResidentService(session).create(payload, actor_id=current_user.id)


# --- resident self-service (must be registered before the /{resident_id}
# routes below, or FastAPI would try to parse "me" as a UUID path param) ---


@router.get("/me", response_model=ResidentRead)
async def get_my_profile(resident: CurrentResident):
    return resident


@router.patch("/me/status", response_model=ResidentRead)
async def set_my_status(session: SessionDep, resident: CurrentResident, payload: ResidentStatusUpdate):
    return await ResidentService(session).set_status(resident.id, payload.status, actor_id=None)


@router.get("/me/activity", response_model=list[ResidentActivityLogRead])
async def my_activity(session: SessionDep, resident: CurrentResident):
    return await ResidentService(session).list_activity(resident.id)


# --- staff/admin/av_bayit views of a specific resident by id ---


@router.get("/{resident_id}", response_model=ResidentRead)
async def get_resident(session: SessionDep, _: NotResident, resident_id: uuid.UUID):
    return await ResidentService(session).get(resident_id)


@router.patch("/{resident_id}", response_model=ResidentRead)
async def update_resident(
    session: SessionDep, current_user: StaffOrAdmin, resident_id: uuid.UUID, payload: ResidentUpdate
):
    return await ResidentService(session).update(resident_id, payload, actor_id=current_user.id)


@router.patch("/{resident_id}/status", response_model=ResidentRead)
async def update_resident_status(
    session: SessionDep, current_user: StaffOrAdmin, resident_id: uuid.UUID, payload: ResidentStatusUpdate
):
    return await ResidentService(session).set_status(resident_id, payload.status, actor_id=current_user.id)


@router.post("/{resident_id}/offboard", response_model=ResidentRead)
async def offboard_resident(
    session: SessionDep,
    current_user: StaffOrAdmin,
    resident_id: uuid.UUID,
    payload: ResidentOffboardRequest = ResidentOffboardRequest(),
):
    return await ResidentService(session).offboard(resident_id, payload, actor_id=current_user.id)


@router.get("/{resident_id}/activity", response_model=list[ResidentActivityLogRead])
async def resident_activity(session: SessionDep, _: NotResident, resident_id: uuid.UUID):
    return await ResidentService(session).list_activity(resident_id)
