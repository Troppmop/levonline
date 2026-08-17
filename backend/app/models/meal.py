import uuid
from datetime import date

from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKey
from app.models.enums import MealInvitationStatus, MealType


class MealHostingRecord(UUIDPrimaryKey, TimestampMixin, table=True):
    """A single hosting event reported by an Av/Eim Bayit family: who they
    hosted and when, for meal coordination reporting."""

    __tablename__ = "meal_hosting_records"

    host_family_name: str = Field(index=True)
    host_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")

    meal_date: date = Field(index=True)
    meal_type: MealType = Field(default=MealType.SHABBAT)

    # A hosted person may or may not be a tracked resident (could be a guest).
    resident_id: uuid.UUID | None = Field(default=None, foreign_key="residents.id", index=True)
    guest_name: str | None = None

    guest_count: int = Field(default=1)
    notes: str | None = None


class MealInvitation(UUIDPrimaryKey, TimestampMixin, table=True):
    """An Av/Eim Bayit family inviting a specific resident to a meal, which
    the resident can accept or decline from their portal. Distinct from
    MealHostingRecord, which is the after-the-fact historical log used for
    hosting reports — an invitation is the forward-looking RSVP workflow.
    """

    __tablename__ = "meal_invitations"

    host_family_name: str = Field(index=True)
    host_user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    resident_id: uuid.UUID = Field(foreign_key="residents.id", index=True, nullable=False)

    meal_date: date = Field(index=True)
    meal_type: MealType = Field(default=MealType.SHABBAT)
    status: MealInvitationStatus = Field(default=MealInvitationStatus.PENDING, index=True)
    notes: str | None = None
