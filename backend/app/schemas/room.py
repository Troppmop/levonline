import uuid

from pydantic import BaseModel


class RoomRead(BaseModel):
    id: uuid.UUID
    floor: int
    room_number: str
    display_order: int
    capacity: int

    model_config = {"from_attributes": True}


class RoomCreate(BaseModel):
    floor: int
    room_number: str
    display_order: int = 0
    capacity: int = 1


class RoomUpdate(BaseModel):
    floor: int | None = None
    room_number: str | None = None
    display_order: int | None = None
    capacity: int | None = None
