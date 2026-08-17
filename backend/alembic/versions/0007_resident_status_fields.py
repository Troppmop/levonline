"""residents: contract_signed, has_horaat_keva, in_country

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "residents", sa.Column("contract_signed", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "residents", sa.Column("has_horaat_keva", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "residents", sa.Column("in_country", sa.Boolean(), nullable=False, server_default="true")
    )
    op.alter_column("residents", "contract_signed", server_default=None)
    op.alter_column("residents", "has_horaat_keva", server_default=None)
    op.alter_column("residents", "in_country", server_default=None)


def downgrade() -> None:
    op.drop_column("residents", "in_country")
    op.drop_column("residents", "has_horaat_keva")
    op.drop_column("residents", "contract_signed")
