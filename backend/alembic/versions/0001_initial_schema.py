"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# name -> member values. Types are created once via raw DDL in upgrade();
# every column reference below builds its own ENUM instance with
# create_type=False so CREATE TABLE never re-issues CREATE TYPE for a type
# that already exists (which errors "already exists" on Postgres).
_ENUM_DEFS: dict[str, list[str]] = {
    "userrole": ["ADMIN", "STAFF", "AV_BAYIT"],
    "residentstatus": ["HOME", "AWAY"],
    "inventorylocation": ["FLOOR_1_KITCHEN", "FLOOR_2_KITCHEN", "FLOOR_3_KITCHEN", "BASEMENT"],
    "inventorycategory": ["PERISHABLE", "NON_PERISHABLE", "CLEANING_SUPPLIES", "PAPER_GOODS", "OTHER"],
    "maintenancestatus": ["NEW", "ACKNOWLEDGED", "IN_PROGRESS", "CLOSED"],
    "mealtype": ["SHABBAT", "YOM_TOV", "WEEKDAY"],
}


def _enum_column(type_name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*_ENUM_DEFS[type_name], name=type_name, create_type=False)


def upgrade() -> None:
    for type_name, values in _ENUM_DEFS.items():
        values_sql = ", ".join(f"'{v}'" for v in values)
        op.execute(f"CREATE TYPE {type_name} AS ENUM ({values_sql})")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", _enum_column("userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("room_number", sa.String(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
    )
    op.create_index("ix_rooms_id", "rooms", ["id"])
    op.create_index("ix_rooms_floor", "rooms", ["floor"])
    op.create_index("ix_rooms_room_number", "rooms", ["room_number"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column(
            "replaced_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("refresh_tokens.id"), nullable=True
        ),
    )
    op.create_index("ix_refresh_tokens_id", "refresh_tokens", ["id"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "residents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rooms.id"), nullable=True),
        sa.Column("status", _enum_column("residentstatus"), nullable=False),
        sa.Column("move_in_date", sa.Date(), nullable=True),
        sa.Column("move_out_date", sa.Date(), nullable=True),
        sa.Column("security_deposit_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("security_deposit_paid", sa.Boolean(), nullable=False),
        sa.Column("security_deposit_paid_date", sa.Date(), nullable=True),
        sa.Column("security_deposit_returned", sa.Boolean(), nullable=False),
        sa.Column("security_deposit_returned_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_residents_id", "residents", ["id"])
    op.create_index("ix_residents_room_id", "residents", ["room_id"])
    op.create_index("ix_residents_status", "residents", ["status"])
    op.create_index("ix_residents_is_active", "residents", ["is_active"])

    op.create_table(
        "resident_activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("residents.id"), nullable=False),
        sa.Column("activity_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_resident_activity_logs_id", "resident_activity_logs", ["id"])
    op.create_index("ix_resident_activity_logs_resident_id", "resident_activity_logs", ["resident_id"])
    op.create_index("ix_resident_activity_logs_activity_type", "resident_activity_logs", ["activity_type"])

    op.create_table(
        "inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", _enum_column("inventorycategory"), nullable=False),
        sa.Column("location", _enum_column("inventorylocation"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("low_stock_threshold", sa.Float(), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("last_restocked_at", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_inventory_items_id", "inventory_items", ["id"])
    op.create_index("ix_inventory_items_name", "inventory_items", ["name"])
    op.create_index("ix_inventory_items_category", "inventory_items", ["category"])
    op.create_index("ix_inventory_items_location", "inventory_items", ["location"])

    op.create_table(
        "inventory_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_items.id"), nullable=False),
        sa.Column("change_quantity", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_inventory_transactions_id", "inventory_transactions", ["id"])
    op.create_index("ix_inventory_transactions_item_id", "inventory_transactions", ["item_id"])

    op.create_table(
        "damage_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", _enum_column("maintenancestatus"), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rooms.id"), nullable=True),
        sa.Column("resident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("residents.id"), nullable=True),
        sa.Column("reported_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("photo_urls", sa.JSON(), nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_damage_reports_id", "damage_reports", ["id"])
    op.create_index("ix_damage_reports_status", "damage_reports", ["status"])
    op.create_index("ix_damage_reports_room_id", "damage_reports", ["room_id"])
    op.create_index("ix_damage_reports_resident_id", "damage_reports", ["resident_id"])

    op.create_table(
        "damage_report_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "damage_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("damage_reports.id"),
            nullable=False,
        ),
        sa.Column("from_status", _enum_column("maintenancestatus"), nullable=True),
        sa.Column("to_status", _enum_column("maintenancestatus"), nullable=False),
        sa.Column("changed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_damage_report_status_history_id", "damage_report_status_history", ["id"])
    op.create_index(
        "ix_damage_report_status_history_damage_report_id",
        "damage_report_status_history",
        ["damage_report_id"],
    )

    op.create_table(
        "meal_hosting_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("host_family_name", sa.String(), nullable=False),
        sa.Column("host_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("meal_date", sa.Date(), nullable=False),
        sa.Column("meal_type", _enum_column("mealtype"), nullable=False),
        sa.Column("resident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("residents.id"), nullable=True),
        sa.Column("guest_name", sa.String(), nullable=True),
        sa.Column("guest_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_meal_hosting_records_id", "meal_hosting_records", ["id"])
    op.create_index("ix_meal_hosting_records_host_family_name", "meal_hosting_records", ["host_family_name"])
    op.create_index("ix_meal_hosting_records_meal_date", "meal_hosting_records", ["meal_date"])
    op.create_index("ix_meal_hosting_records_resident_id", "meal_hosting_records", ["resident_id"])


def downgrade() -> None:
    op.drop_table("meal_hosting_records")
    op.drop_table("damage_report_status_history")
    op.drop_table("damage_reports")
    op.drop_table("inventory_transactions")
    op.drop_table("inventory_items")
    op.drop_table("resident_activity_logs")
    op.drop_table("residents")
    op.drop_table("refresh_tokens")
    op.drop_table("rooms")
    op.drop_table("users")

    for type_name in reversed(list(_ENUM_DEFS)):
        op.execute(f"DROP TYPE {type_name}")
