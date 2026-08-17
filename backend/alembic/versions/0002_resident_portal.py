"""resident portal: RESIDENT role, announcements, meal invitations, report categories

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_ENUM_DEFS: dict[str, list[str]] = {
    "reportcategory": ["DAMAGE", "CLEANING"],
    "announcementcategory": ["GENERAL", "TEFILLAH_TIMES", "EMERGENCY"],
    "mealinvitationstatus": ["PENDING", "ACCEPTED", "DECLINED"],
}


def _enum_column(type_name: str, values: list[str]) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=type_name, create_type=False)


def upgrade() -> None:
    for type_name, values in _NEW_ENUM_DEFS.items():
        values_sql = ", ".join(f"'{v}'" for v in values)
        op.execute(f"CREATE TYPE {type_name} AS ENUM ({values_sql})")

    # New value on an existing enum type: cannot be used in an INSERT/UPDATE
    # within the same transaction it's added in, but that's fine here since
    # this migration only changes schema, not data.
    op.execute("ALTER TYPE userrole ADD VALUE 'RESIDENT'")

    # Both FKs below are named explicitly (rather than left to Postgres's
    # auto-generated names) to match the SQLModel definitions in
    # app/models/user.py and app/models/resident.py — users <-> residents
    # is a circular FK pair, and SQLAlchemy's metadata-driven drop_all
    # (used by tests and the /testing/reset endpoint) can only break that
    # cycle if the constraint names in its metadata match reality.
    op.add_column(
        "users",
        sa.Column(
            "resident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("residents.id", name="fk_users_resident_id"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_resident_id", "users", ["resident_id"], unique=True)

    op.add_column(
        "residents",
        sa.Column(
            "assigned_av_bayit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_residents_assigned_av_bayit_id"),
            nullable=True,
        ),
    )
    op.create_index("ix_residents_assigned_av_bayit_id", "residents", ["assigned_av_bayit_id"])

    op.add_column(
        "damage_reports",
        sa.Column(
            "category",
            _enum_column("reportcategory", _NEW_ENUM_DEFS["reportcategory"]),
            nullable=False,
            server_default="DAMAGE",
        ),
    )
    op.create_index("ix_damage_reports_category", "damage_reports", ["category"])
    # Drop the server_default now that existing rows are backfilled — new
    # rows always specify category explicitly via the application.
    op.alter_column("damage_reports", "category", server_default=None)

    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "category",
            _enum_column("announcementcategory", _NEW_ENUM_DEFS["announcementcategory"]),
            nullable=False,
        ),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column(
            "audience_av_bayit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_announcements_id", "announcements", ["id"])
    op.create_index("ix_announcements_category", "announcements", ["category"])
    op.create_index("ix_announcements_pinned", "announcements", ["pinned"])
    op.create_index("ix_announcements_audience_av_bayit_id", "announcements", ["audience_av_bayit_id"])

    op.create_table(
        "meal_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("host_family_name", sa.String(), nullable=False),
        sa.Column("host_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "resident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("residents.id"), nullable=False
        ),
        sa.Column("meal_date", sa.Date(), nullable=False),
        sa.Column("meal_type", _enum_column("mealtype", ["SHABBAT", "YOM_TOV", "WEEKDAY"]), nullable=False),
        sa.Column(
            "status",
            _enum_column("mealinvitationstatus", _NEW_ENUM_DEFS["mealinvitationstatus"]),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_meal_invitations_id", "meal_invitations", ["id"])
    op.create_index("ix_meal_invitations_host_family_name", "meal_invitations", ["host_family_name"])
    op.create_index("ix_meal_invitations_host_user_id", "meal_invitations", ["host_user_id"])
    op.create_index("ix_meal_invitations_resident_id", "meal_invitations", ["resident_id"])
    op.create_index("ix_meal_invitations_meal_date", "meal_invitations", ["meal_date"])
    op.create_index("ix_meal_invitations_status", "meal_invitations", ["status"])


def downgrade() -> None:
    op.drop_table("meal_invitations")
    op.drop_table("announcements")

    op.drop_index("ix_damage_reports_category", table_name="damage_reports")
    op.drop_column("damage_reports", "category")

    op.drop_index("ix_residents_assigned_av_bayit_id", table_name="residents")
    op.drop_column("residents", "assigned_av_bayit_id")

    op.drop_index("ix_users_resident_id", table_name="users")
    op.drop_column("users", "resident_id")

    # Postgres has no ALTER TYPE ... DROP VALUE; rebuilding the enum without
    # RESIDENT would require rewriting every column that uses it. Not worth
    # it for a downgrade path — leaving the unused enum label is harmless.

    for type_name in reversed(list(_NEW_ENUM_DEFS)):
        op.execute(f"DROP TYPE {type_name}")
