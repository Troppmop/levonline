import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKey
from app.models.enums import RegistrationStatus


class ResidentRegistrationRequest(UUIDPrimaryKey, TimestampMixin, table=True):
    """A soldier's self-submitted request for a resident account. Nothing
    in `users` or `residents` exists until an admin/staff approves this —
    approval is the moment both get created, so there's never a half-active
    login floating around while a request is still pending.

    No unique constraint on email: a rejected applicant can submit again,
    and we keep the old rejected row for history rather than overwriting it.
    """

    __tablename__ = "resident_registration_requests"

    first_name: str
    last_name: str
    email: str = Field(index=True)
    phone: str | None = None
    hashed_password: str
    status: RegistrationStatus = Field(default=RegistrationStatus.PENDING, index=True)

    review_note: str | None = None
    reviewed_by_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    reviewed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    # Set on approval, for traceability from the application back to the
    # resident/room it became.
    created_resident_id: uuid.UUID | None = Field(default=None, foreign_key="residents.id")
