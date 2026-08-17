import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ResidentStatus
from app.schemas.room import RoomRead


class ResidentBase(BaseModel):
    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None
    room_id: uuid.UUID | None = None
    assigned_av_bayit_id: uuid.UUID | None = None
    move_in_date: date | None = None
    move_out_date: date | None = None
    security_deposit_amount: Decimal = Decimal("0")
    security_deposit_paid: bool = False
    security_deposit_paid_date: date | None = None
    security_deposit_returned: bool = False
    security_deposit_returned_date: date | None = None
    rent_amount_due: Decimal = Decimal("0")
    rent_amount_paid: Decimal = Decimal("0")
    contract_pdf_url: str | None = None
    contract_signed: bool = False
    has_horaat_keva: bool = False
    in_country: bool = True
    notes: str | None = None


class ResidentCreate(ResidentBase):
    status: ResidentStatus = ResidentStatus.HOME


class ResidentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    room_id: uuid.UUID | None = None
    assigned_av_bayit_id: uuid.UUID | None = None
    status: ResidentStatus | None = None
    move_in_date: date | None = None
    move_out_date: date | None = None
    security_deposit_amount: Decimal | None = None
    security_deposit_paid: bool | None = None
    security_deposit_paid_date: date | None = None
    security_deposit_returned: bool | None = None
    security_deposit_returned_date: date | None = None
    rent_amount_due: Decimal | None = None
    rent_amount_paid: Decimal | None = None
    contract_pdf_url: str | None = None
    contract_signed: bool | None = None
    has_horaat_keva: bool | None = None
    in_country: bool | None = None
    notes: str | None = None
    is_active: bool | None = None


class ResidentStatusUpdate(BaseModel):
    status: ResidentStatus


class ResidentOffboardRequest(BaseModel):
    """Checklist confirmations collected in the Offboard Resident modal;
    folded into the activity log description rather than stored as
    separate columns, since they're a one-time procedural record."""

    key_returned: bool = False
    biometric_cleared: bool = False
    balance_settled: bool = False
    note: str | None = None


class ResidentRead(ResidentBase):
    id: uuid.UUID
    status: ResidentStatus
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    room: RoomRead | None = None

    model_config = {"from_attributes": True}


class ResidentActivityLogRead(BaseModel):
    id: uuid.UUID
    resident_id: uuid.UUID
    activity_type: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomWithResidents(RoomRead):
    """Presence tracker unit: a room plus the residents assigned to it,
    used to render the Home/Away board by physical layout."""

    residents: list[ResidentRead] = []
