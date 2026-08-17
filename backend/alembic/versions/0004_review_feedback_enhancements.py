"""review feedback: rent tracking + offboarding, report locations, event details, kiddush inventory location

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New value on an existing enum type: cannot be used in the same
    # transaction it's added in, but this migration only changes schema.
    op.execute("ALTER TYPE inventorylocation ADD VALUE 'KIDDUSH_SUPPLY_ROOM'")

    op.add_column(
        "residents", sa.Column("rent_amount_due", sa.Numeric(10, 2), nullable=False, server_default="0")
    )
    op.add_column(
        "residents", sa.Column("rent_amount_paid", sa.Numeric(10, 2), nullable=False, server_default="0")
    )
    op.add_column("residents", sa.Column("contract_pdf_url", sa.String(), nullable=True))
    op.add_column(
        "residents", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false")
    )
    op.create_index("ix_residents_is_archived", "residents", ["is_archived"])
    # Drop server defaults now that existing rows are backfilled — new rows
    # always specify these explicitly via the application.
    op.alter_column("residents", "rent_amount_due", server_default=None)
    op.alter_column("residents", "rent_amount_paid", server_default=None)
    op.alter_column("residents", "is_archived", server_default=None)

    op.add_column("damage_reports", sa.Column("location_detail", sa.String(), nullable=True))

    op.add_column("announcements", sa.Column("event_location", sa.String(), nullable=True))
    op.add_column("announcements", sa.Column("event_time", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("announcements", "event_time")
    op.drop_column("announcements", "event_location")

    op.drop_column("damage_reports", "location_detail")

    op.drop_index("ix_residents_is_archived", table_name="residents")
    op.drop_column("residents", "is_archived")
    op.drop_column("residents", "contract_pdf_url")
    op.drop_column("residents", "rent_amount_paid")
    op.drop_column("residents", "rent_amount_due")

    # Postgres has no ALTER TYPE ... DROP VALUE; leaving the unused enum
    # label is harmless (same tradeoff made in 0002 for RESIDENT).
