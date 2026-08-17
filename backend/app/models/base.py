import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class UUIDPrimaryKey(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)


class TimestampMixin(SQLModel):
    # sa_type=DateTime(timezone=True): SQLModel's default mapping for a bare
    # `datetime` field is a naive TIMESTAMP column. We always write
    # tz-aware UTC values (utcnow() above), and asyncpg rejects binding an
    # aware datetime into a naive column outright (unlike SQLite, which
    # silently accepts either) — this failed against real Postgres despite
    # passing every SQLite-backed test.
    created_at: datetime = Field(default_factory=utcnow, nullable=False, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": utcnow},
    )
