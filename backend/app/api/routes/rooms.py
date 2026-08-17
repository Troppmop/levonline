import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep, StaffOrAdmin
from app.models.room import Room
from app.repositories.room_repository import RoomRepository
from app.schemas.room import RoomCreate, RoomRead, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomRead])
async def list_rooms(session: SessionDep, _: CurrentUser):
    rooms = await RoomRepository(session).list(limit=1000)
    return sorted(rooms, key=lambda r: (r.floor, r.display_order, r.room_number))


@router.post("", response_model=RoomRead, status_code=201)
async def create_room(session: SessionDep, _: StaffOrAdmin, payload: RoomCreate):
    room = Room(**payload.model_dump())
    return await RoomRepository(session).create(room)


@router.patch("/{room_id}", response_model=RoomRead)
async def update_room(session: SessionDep, _: StaffOrAdmin, room_id: uuid.UUID, payload: RoomUpdate):
    repo = RoomRepository(session)
    room = await repo.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return await repo.update(room, payload.model_dump(exclude_unset=True))
