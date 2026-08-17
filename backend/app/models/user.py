import uuid

from sqlalchemy import Column, ForeignKey, Uuid
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKey
from app.models.enums import UserRole


class User(UUIDPrimaryKey, TimestampMixin, table=True):
    __tablename__ = "users"

    email: str = Field(index=True, unique=True, nullable=False)
    hashed_password: str
    full_name: str
    role: UserRole = Field(default=UserRole.STAFF)
    is_active: bool = Field(default=True)
    avatar_url: str | None = None

    # Only set (and only meaningful) for role=RESIDENT: links the login
    # account to the resident profile it's allowed to see/edit. Nullable
    # because staff/admin/av_bayit accounts have no resident profile.
    #
    # Named + use_alter=True: users <-> residents is a circular FK
    # (residents also references users.id via assigned_av_bayit_id).
    # SQLAlchemy's metadata-driven create_all/drop_all can only break that
    # cycle — by issuing this constraint via a separate ALTER TABLE instead
    # of inline in CREATE TABLE — if it's both named AND marked use_alter.
    # Naming alone isn't enough (discovered when the /testing/reset
    # endpoint's drop_all failed against real Postgres despite working on
    # SQLite, which doesn't enforce FK ordering the same way).
    resident_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid,
            ForeignKey("residents.id", name="fk_users_resident_id", use_alter=True),
            unique=True,
        ),
    )
