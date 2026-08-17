import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import RegistrationStatus


class RegistrationRequestCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    # max_length=72: bcrypt silently ignores bytes beyond 72, so longer
    # inputs would compare unequal in confusing ways; reject them up front.
    password: str = Field(min_length=8, max_length=72)


class RegistrationRequestRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    status: RegistrationStatus
    review_note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RegistrationApprove(BaseModel):
    room_id: uuid.UUID | None = None


class RegistrationReject(BaseModel):
    note: str | None = None
