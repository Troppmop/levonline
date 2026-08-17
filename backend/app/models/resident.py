import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, ForeignKey, Uuid
from sqlmodel import Field, Relationship

from app.models.base import TimestampMixin, UUIDPrimaryKey
from app.models.enums import ResidentStatus

if TYPE_CHECKING:
    from app.models.maintenance import DamageReport
    from app.models.room import Room


class Resident(UUIDPrimaryKey, TimestampMixin, table=True):
    __tablename__ = "residents"

    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None

    room_id: uuid.UUID | None = Field(default=None, foreign_key="rooms.id", index=True)
    status: ResidentStatus = Field(default=ResidentStatus.HOME, index=True)

    # The Av/Eim Bayit family responsible for this resident's meal hosting;
    # drives "my assigned soldiers" queries and group-targeted announcements.
    #
    # Named explicitly: this and User.resident_id form a circular FK
    # (residents -> users -> residents), which SQLAlchemy's metadata-driven
    # drop_all can only handle if at least one side's constraint has a name
    # to drop independently before dropping the table. See the comment on
    # User.resident_id for the full story.
    assigned_av_bayit_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid, ForeignKey("users.id", name="fk_residents_assigned_av_bayit_id"), index=True
        ),
    )

    # Housing info
    move_in_date: date | None = None
    move_out_date: date | None = None

    # Security deposit
    security_deposit_amount: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)
    security_deposit_paid: bool = Field(default=False)
    security_deposit_paid_date: date | None = None
    security_deposit_returned: bool = Field(default=False)
    security_deposit_returned_date: date | None = None

    # Rent balance tracking (a lightweight running total, not a full ledger).
    rent_amount_due: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)
    rent_amount_paid: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)
    contract_pdf_url: str | None = None

    notes: str | None = None
    is_active: bool = Field(default=True, index=True)
    # Set by the offboarding flow; drives the Active/Former-Resident tabs.
    # Kept alongside is_active (always toggled together) rather than
    # replacing it, since is_active is already relied on elsewhere.
    is_archived: bool = Field(default=False, index=True)

    room: Optional["Room"] = Relationship(back_populates="residents")
    activity_logs: list["ResidentActivityLog"] = Relationship(
        back_populates="resident",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    damage_reports: list["DamageReport"] = Relationship(back_populates="resident")


class ResidentActivityLog(UUIDPrimaryKey, TimestampMixin, table=True):
    """Append-only audit trail of notable events for a resident's profile
    (status changes, deposit updates, notes added, etc.)."""

    __tablename__ = "resident_activity_logs"

    resident_id: uuid.UUID = Field(foreign_key="residents.id", index=True, nullable=False)
    activity_type: str = Field(index=True)
    description: str
    created_by_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")

    resident: Resident | None = Relationship(back_populates="activity_logs")
