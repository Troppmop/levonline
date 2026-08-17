import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKey


class RefreshToken(UUIDPrimaryKey, TimestampMixin, table=True):
    """Stores only the hash of the refresh token value, never the raw token.

    Rotation strategy: each use of a refresh token immediately revokes it and
    issues a new one linked via `replaced_by_id`. If a revoked token is
    presented again, it indicates token theft/replay and the whole chain
    (and thus the user's session) should be invalidated.
    """

    __tablename__ = "refresh_tokens"

    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    token_hash: str = Field(index=True, unique=True, nullable=False)
    expires_at: datetime = Field(nullable=False, sa_type=DateTime(timezone=True))
    revoked: bool = Field(default=False)
    replaced_by_id: uuid.UUID | None = Field(default=None, foreign_key="refresh_tokens.id")
