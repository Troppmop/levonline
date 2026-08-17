"""self-registration: resident_registration_requests table

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REGISTRATION_STATUS_VALUES = ["PENDING", "APPROVED", "REJECTED"]


def upgrade() -> None:
    values_sql = ", ".join(f"'{v}'" for v in _REGISTRATION_STATUS_VALUES)
    op.execute(f"CREATE TYPE registrationstatus AS ENUM ({values_sql})")

    op.create_table(
        "resident_registration_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(*_REGISTRATION_STATUS_VALUES, name="registrationstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_resident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("residents.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_resident_registration_requests_id", "resident_registration_requests", ["id"])
    op.create_index(
        "ix_resident_registration_requests_email", "resident_registration_requests", ["email"]
    )
    op.create_index(
        "ix_resident_registration_requests_status", "resident_registration_requests", ["status"]
    )


def downgrade() -> None:
    op.drop_table("resident_registration_requests")
    op.execute("DROP TYPE registrationstatus")
