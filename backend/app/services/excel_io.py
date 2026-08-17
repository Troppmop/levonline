"""Generic Excel import/export engine for admin bulk data management.

Works off each SQLModel table's own pydantic field definitions rather than
hand-written per-table column lists, so adding a new table to
`TABLE_REGISTRY` is the only step needed to get import/export for it.

Design notes (see README/DOCUMENTATION for the full write-up):
- `users` is export/update-only — `hashed_password` is never exported, and
  import can't create a new login (there's no password to hash), only
  update fields on an existing one. New logins are created from Admin ->
  Staff Accounts, which controls the password.
- Import is all-or-nothing: every row is validated first; if *any* row
  fails, nothing is written and the full list of per-row errors is
  returned. Only a fully clean file is applied and committed.
"""

import io
import json
import types
import typing
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum

import pandas as pd
from fastapi import UploadFile
from pydantic.fields import FieldInfo
from sqlalchemy import select
from sqlmodel import SQLModel

from app.models.announcement import Announcement
from app.models.inventory import InventoryItem
from app.models.maintenance import DamageReport
from app.models.meal import MealHostingRecord
from app.models.resident import Resident
from app.models.room import Room
from app.models.user import User


@dataclass
class TableSpec:
    model: type[SQLModel]
    label: str
    exclude_fields: frozenset[str] = field(default_factory=frozenset)
    readonly_fields: frozenset[str] = frozenset({"id", "created_at", "updated_at"})
    unique_fields: tuple[str, ...] | None = None
    allow_create: bool = True


# Order matters for import_all_tables: a row referencing another table by
# FK (e.g. a resident's room_id) can only resolve if that table was already
# applied earlier in the same batch — so this is roughly FK-dependency
# order, not just alphabetical/display order.
TABLE_REGISTRY: dict[str, TableSpec] = {
    "users": TableSpec(
        model=User,
        label="Users",
        # Never export/import password hashes through a spreadsheet.
        exclude_fields=frozenset({"hashed_password"}),
        unique_fields=("email",),
        allow_create=False,
    ),
    "rooms": TableSpec(model=Room, label="Rooms", unique_fields=("floor", "room_number")),
    "residents": TableSpec(model=Resident, label="Residents"),
    "inventory_items": TableSpec(
        model=InventoryItem, label="Inventory Items", unique_fields=("name", "location")
    ),
    "damage_reports": TableSpec(model=DamageReport, label="Maintenance & Cleaning Reports"),
    "meal_hosting_records": TableSpec(model=MealHostingRecord, label="Meal Hosting Records"),
    "announcements": TableSpec(model=Announcement, label="Announcements"),
}


def list_tables() -> list[dict]:
    return [{"table_name": name, "label": spec.label} for name, spec in TABLE_REGISTRY.items()]


def get_table_spec(table_name: str) -> TableSpec:
    spec = TABLE_REGISTRY.get(table_name)
    if spec is None:
        raise KeyError(f"Unknown table '{table_name}'")
    return spec


# --- column introspection -----------------------------------------------


def _unwrap_optional(annotation: object) -> tuple[object, bool]:
    """Given a field annotation like `str | None`, returns (str, True).
    Non-optional annotations pass through unchanged with False."""
    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is types.UnionType:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0], True
    return annotation, False


def _exportable_fields(spec: TableSpec) -> list[str]:
    return [name for name in spec.model.model_fields if name not in spec.exclude_fields]


def _writable_fields(spec: TableSpec) -> list[str]:
    return [
        name
        for name in _exportable_fields(spec)
        if name not in spec.readonly_fields
    ]


def _describe_type(annotation: object) -> tuple[str, list[str] | None]:
    target, _ = _unwrap_optional(annotation)
    if target is uuid.UUID:
        return "UUID", None
    if isinstance(target, type) and issubclass(target, Enum):
        return "choice", [m.value for m in target]
    if target is bool:
        return "true/false", None
    if target is Decimal:
        return "number (decimal)", None
    if target is int:
        return "integer", None
    if target is float:
        return "number", None
    if target is datetime:
        return "datetime (ISO 8601, e.g. 2026-01-15T14:00:00Z)", None
    if target is date:
        return "date (YYYY-MM-DD)", None
    if target is list or typing.get_origin(target) is list:
        return "list (comma-separated, or a JSON array)", None
    return "text", None


def describe_table(table_name: str) -> dict:
    """Powers the Data Management 'View Schema' panel — column-by-column
    type/required info so an admin knows what a valid import file needs,
    without having to reverse-engineer it from a failed upload."""
    spec = get_table_spec(table_name)
    writable = set(_writable_fields(spec))
    columns = []
    for name in _exportable_fields(spec):
        field_info = _field_info(spec, name)
        type_label, choices = _describe_type(field_info.annotation)
        columns.append(
            {
                "name": name,
                "type": type_label,
                "choices": choices,
                "required": field_info.is_required() and name in writable,
                "writable": name in writable,
            }
        )
    return {
        "table_name": table_name,
        "label": spec.label,
        "columns": columns,
        "allow_create": spec.allow_create,
        "match_fields": list(spec.unique_fields) if spec.unique_fields else ["id"],
    }


# --- export ---------------------------------------------------------------


def _cell_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, list):
        return json.dumps(value)
    return value


def _rows_for_export(spec: TableSpec, instances: list[SQLModel]) -> pd.DataFrame:
    columns = _exportable_fields(spec)
    rows = [{col: _cell_value(getattr(obj, col)) for col in columns} for obj in instances]
    return pd.DataFrame(rows, columns=columns)


async def export_table_xlsx(session, table_name: str) -> tuple[str, bytes]:
    spec = get_table_spec(table_name)
    result = await session.execute(select(spec.model))
    instances = result.scalars().all()
    df = _rows_for_export(spec, list(instances))

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=table_name[:31], index=False)
    buffer.seek(0)
    return f"{table_name}.xlsx", buffer.read()


async def export_all_xlsx(session) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for table_name, spec in TABLE_REGISTRY.items():
            result = await session.execute(select(spec.model))
            instances = result.scalars().all()
            df = _rows_for_export(spec, list(instances))
            df.to_excel(writer, sheet_name=table_name[:31], index=False)
    buffer.seek(0)
    return buffer.read()


def build_template_xlsx(table_name: str) -> bytes:
    """Header-only workbook (writable columns only) for the import dropzone's
    'download template' link — id/created_at/updated_at are server-managed
    and deliberately left off so users don't try to hand-author them."""
    spec = get_table_spec(table_name)
    df = pd.DataFrame(columns=_writable_fields(spec))
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=table_name[:31], index=False)
    buffer.seek(0)
    return buffer.read()


# --- import -----------------------------------------------------------


class RowError(typing.TypedDict):
    row: int
    column: str | None
    message: str


@dataclass
class ImportResult:
    inserted_count: int
    updated_count: int
    errors: list[RowError]


def _field_info(spec: TableSpec, column: str) -> FieldInfo:
    return spec.model.model_fields[column]


def _parse_cell(column: str, field_info: FieldInfo, raw: object) -> object:
    """Converts a raw pandas cell value into the Python type the model
    field expects. Raises ValueError with a human-readable message on any
    conversion failure — callers turn that into a RowError."""
    target, optional = _unwrap_optional(field_info.annotation)

    is_blank = (
        raw is None
        or (isinstance(raw, float) and pd.isna(raw))
        or (isinstance(raw, str) and raw.strip() == "")
    )
    if is_blank:
        if optional or not field_info.is_required():
            return None
        raise ValueError(f"'{column}' is required")

    if target is uuid.UUID:
        return uuid.UUID(str(raw).strip())
    if isinstance(target, type) and issubclass(target, Enum):
        raw_str = str(raw).strip().lower()
        try:
            return target(raw_str)
        except ValueError:
            choices = ", ".join(m.value for m in target)
            raise ValueError(f"'{column}' must be one of: {choices}") from None
    if target is bool:
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {"true", "1", "yes", "y"}
    if target is Decimal:
        try:
            return Decimal(str(raw).strip())
        except InvalidOperation:
            raise ValueError(f"'{column}' must be a number") from None
    if target is datetime:
        if isinstance(raw, pd.Timestamp):
            dt = raw.to_pydatetime()
        else:
            dt = datetime.fromisoformat(str(raw).strip())
        if dt.tzinfo is None:
            from datetime import UTC

            dt = dt.replace(tzinfo=UTC)
        return dt
    if target is date:
        if isinstance(raw, pd.Timestamp):
            return raw.date()
        if isinstance(raw, datetime):
            return raw.date()
        return date.fromisoformat(str(raw).strip()[:10])
    if target is list or typing.get_origin(target) is list:
        if isinstance(raw, list):
            return raw
        try:
            return json.loads(str(raw))
        except json.JSONDecodeError:
            return [part.strip() for part in str(raw).split(",") if part.strip()]
    if target is int:
        return int(float(raw))
    if target is float:
        return float(raw)
    return str(raw)


def _read_upload_dataframe(filename: str, content: bytes) -> pd.DataFrame:
    buffer = io.BytesIO(content)
    if filename.lower().endswith(".csv"):
        return pd.read_csv(buffer)
    return pd.read_excel(buffer, engine="openpyxl")


async def _validate_dataframe(
    session, spec: TableSpec, df: pd.DataFrame
) -> tuple[list[RowError], list[tuple[SQLModel | None, dict]]]:
    """Validates + resolves every row's target (insert vs. update) without
    touching the session, so a caller can check for zero errors across one
    or many sheets before writing anything."""
    writable = set(_writable_fields(spec))
    # A round-tripped export legitimately includes id/created_at/updated_at
    # even though they're not writable — those get ignored below, not
    # flagged as unknown. Only a column that isn't part of the table at
    # all (typo, wrong sheet, stray column) is an error.
    known_columns = writable | set(spec.readonly_fields)
    unknown_columns = [c for c in df.columns if c not in known_columns]

    errors: list[RowError] = []
    if unknown_columns:
        errors.append(
            {
                "row": 0,
                "column": ", ".join(unknown_columns),
                "message": f"Unknown column(s) — not part of the {spec.label} template",
            }
        )

    parsed_rows: list[tuple[SQLModel | None, dict]] = []
    for idx, raw_row in df.iterrows():
        row_num = int(idx) + 2  # +1 for 0-index, +1 for the header row
        row_dict = raw_row.to_dict()
        parsed: dict[str, object] = {}
        row_had_error = False

        for column in df.columns:
            if column == "id" or column not in writable:
                continue
            field_info = _field_info(spec, column)
            try:
                parsed[column] = _parse_cell(column, field_info, row_dict.get(column))
            except (ValueError, TypeError) as exc:
                errors.append({"row": row_num, "column": column, "message": str(exc)})
                row_had_error = True

        if row_had_error:
            continue

        try:
            existing = await _resolve_existing(session, spec, df, row_dict)
        except _RowIdNotFound:
            errors.append(
                {"row": row_num, "column": "id", "message": "No existing row matches this id"}
            )
            continue

        if existing is None and not spec.allow_create:
            errors.append(
                {
                    "row": row_num,
                    "column": None,
                    "message": f"No existing row matched this {spec.label} entry (by "
                    f"{'/'.join(spec.unique_fields) if spec.unique_fields else 'id'}), and creating "
                    "new rows for this table isn't supported via import.",
                }
            )
            continue

        if existing is None:
            missing_required = [
                col
                for col in writable
                if col not in df.columns and _field_info(spec, col).is_required()
            ]
            if missing_required:
                errors.append(
                    {
                        "row": row_num,
                        "column": ", ".join(missing_required),
                        "message": "Required column(s) missing — needed to create a new row",
                    }
                )
                continue

        parsed_rows.append((existing, parsed))

    return errors, parsed_rows


def _apply_parsed_rows(session, spec: TableSpec, parsed_rows: list[tuple[SQLModel | None, dict]]) -> None:
    for existing, parsed in parsed_rows:
        if existing is not None:
            for k, v in parsed.items():
                setattr(existing, k, v)
            session.add(existing)
        else:
            obj = spec.model(**parsed)
            session.add(obj)


async def import_table(
    session,
    table_name: str,
    upload: UploadFile,
    actor_id: uuid.UUID | None = None,
    dry_run: bool = False,
) -> ImportResult:
    spec = get_table_spec(table_name)
    content = await upload.read()
    df = _read_upload_dataframe(upload.filename or "", content)

    errors, parsed_rows = await _validate_dataframe(session, spec, df)
    if errors:
        return ImportResult(inserted_count=0, updated_count=0, errors=errors)

    inserted = sum(1 for existing, _ in parsed_rows if existing is None)
    updated = len(parsed_rows) - inserted

    if dry_run:
        # Validated cleanly, but the caller only wanted a preview — don't
        # touch the session at all.
        return ImportResult(inserted_count=inserted, updated_count=updated, errors=[])

    _apply_parsed_rows(session, spec, parsed_rows)
    await session.flush()
    return ImportResult(inserted_count=inserted, updated_count=updated, errors=[])


async def import_all_tables(session, upload: UploadFile, dry_run: bool = False) -> dict[str, ImportResult]:
    """Imports a multi-sheet workbook (the same shape export_all_xlsx
    produces) — one sheet per table, matched by sheet name to
    TABLE_REGISTRY. Sheets for unknown tables are ignored; a table with no
    matching sheet is simply left untouched.

    Atomic across the *entire* workbook, not just per-sheet: if any row on
    any sheet fails validation, nothing on any sheet is written.
    """
    content = await upload.read()
    if (upload.filename or "").lower().endswith(".csv"):
        raise ValueError("A multi-table import needs a multi-sheet .xlsx workbook, not a .csv file")
    sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, engine="openpyxl")

    validated: dict[str, tuple[list[RowError], list[tuple[SQLModel | None, dict]]]] = {}
    for table_name, spec in TABLE_REGISTRY.items():
        if table_name not in sheets:
            continue
        validated[table_name] = await _validate_dataframe(session, spec, sheets[table_name])

    any_errors = any(errors for errors, _ in validated.values())

    results: dict[str, ImportResult] = {}
    for table_name, (errors, parsed_rows) in validated.items():
        if any_errors:
            results[table_name] = ImportResult(inserted_count=0, updated_count=0, errors=errors)
            continue

        inserted = sum(1 for existing, _ in parsed_rows if existing is None)
        updated = len(parsed_rows) - inserted
        if not dry_run:
            _apply_parsed_rows(session, TABLE_REGISTRY[table_name], parsed_rows)
        results[table_name] = ImportResult(inserted_count=inserted, updated_count=updated, errors=[])

    if not any_errors and not dry_run:
        await session.flush()

    return results


class _RowIdNotFound(Exception):
    """An `id` column value was supplied but doesn't match any row —
    treated as a hard error rather than silently falling through to an
    insert, since a stale/typo'd id is far more likely than an intentional
    'create with this exact id' request."""


async def _resolve_existing(session, spec: TableSpec, df: pd.DataFrame, row_dict: dict) -> SQLModel | None:
    if "id" in df.columns:
        raw_id = row_dict.get("id")
        if raw_id is not None and not (isinstance(raw_id, float) and pd.isna(raw_id)) and str(raw_id).strip():
            existing = await session.get(spec.model, uuid.UUID(str(raw_id).strip()))
            if existing is None:
                raise _RowIdNotFound
            return existing

    if spec.unique_fields:
        stmt = select(spec.model)
        matchable = True
        for uf in spec.unique_fields:
            value = row_dict.get(uf)
            if value is None or (isinstance(value, float) and pd.isna(value)):
                matchable = False
                break
            stmt = stmt.where(getattr(spec.model, uf) == value)
        if matchable:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    return None
