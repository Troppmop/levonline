import uuid
from datetime import date, datetime

from pydantic import BaseModel, model_validator

from app.models.enums import MealInvitationStatus, MealType


class MealHostingRecordBase(BaseModel):
    host_family_name: str
    meal_date: date
    meal_type: MealType = MealType.SHABBAT
    resident_id: uuid.UUID | None = None
    guest_name: str | None = None
    guest_count: int = 1
    notes: str | None = None

    @model_validator(mode="after")
    def require_guest_identity(self):
        if self.resident_id is None and not self.guest_name:
            raise ValueError("Either resident_id or guest_name must be provided")
        return self


class MealHostingRecordCreate(MealHostingRecordBase):
    pass


class MealHostingRecordRead(MealHostingRecordBase):
    id: uuid.UUID
    host_user_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MealHostingSummary(BaseModel):
    """Aggregated report of who hosted how often over a date range, for
    Av/Eim Bayit coordination reporting."""

    host_family_name: str
    total_meals_hosted: int
    total_guests_hosted: int


class MealInvitationCreate(BaseModel):
    host_family_name: str
    resident_id: uuid.UUID
    meal_date: date
    meal_type: MealType = MealType.SHABBAT
    notes: str | None = None


class MealInvitationRespond(BaseModel):
    status: MealInvitationStatus

    @model_validator(mode="after")
    def must_be_a_response(self):
        if self.status == MealInvitationStatus.PENDING:
            raise ValueError("status must be 'accepted' or 'declined'")
        return self


class MealInvitationRead(BaseModel):
    id: uuid.UUID
    host_family_name: str
    host_user_id: uuid.UUID
    resident_id: uuid.UUID
    meal_date: date
    meal_type: MealType
    status: MealInvitationStatus
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
