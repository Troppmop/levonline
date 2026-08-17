from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.deps import AdminOnly, SessionDep
from app.services import excel_io

router = APIRouter(prefix="/admin", tags=["admin-data"])

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx_response(filename: str, content: bytes) -> Response:
    return Response(
        content=content,
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/data-tables")
async def list_data_tables(_: AdminOnly) -> list[dict]:
    """Backs the Data Management tab's table picker — the frontend never
    hardcodes table names, so this list is the single source of truth."""
    return excel_io.list_tables()


@router.get("/export/{table_name}")
async def export_table(table_name: str, _: AdminOnly, session: SessionDep, format: str = "xlsx"):
    if format != "xlsx":
        raise HTTPException(status_code=400, detail="Only format=xlsx is supported")
    try:
        filename, content = await excel_io.export_table_xlsx(session, table_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _xlsx_response(filename, content)


@router.get("/export-all")
async def export_all(_: AdminOnly, session: SessionDep):
    content = await excel_io.export_all_xlsx(session)
    return _xlsx_response("lev-lachayal-full-export.xlsx", content)


@router.get("/schema/{table_name}")
async def get_table_schema(table_name: str, _: AdminOnly) -> dict:
    try:
        return excel_io.describe_table(table_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/import-template/{table_name}")
async def import_template(table_name: str, _: AdminOnly):
    try:
        content = excel_io.build_template_xlsx(table_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _xlsx_response(f"{table_name}-template.xlsx", content)


@router.post("/import/{table_name}")
async def import_table(
    table_name: str,
    session: SessionDep,
    current_user: AdminOnly,
    file: UploadFile = File(...),
    dry_run: bool = False,
) -> dict:
    try:
        result = await excel_io.import_table(
            session, table_name, file, actor_id=current_user.id, dry_run=dry_run
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        # Unreadable file (corrupt workbook, wrong extension content, etc.)
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}") from exc
    return {
        "inserted_count": result.inserted_count,
        "updated_count": result.updated_count,
        "errors": result.errors,
        "dry_run": dry_run,
    }


@router.post("/import-all")
async def import_all(
    session: SessionDep, _: AdminOnly, file: UploadFile = File(...), dry_run: bool = False
) -> dict:
    """Takes the same multi-sheet workbook export-all produces, edited and
    sent back — one sheet per table, atomic across the whole file."""
    try:
        results = await excel_io.import_all_tables(session, file, dry_run=dry_run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}") from exc
    return {
        "dry_run": dry_run,
        "tables": {
            table_name: {
                "inserted_count": result.inserted_count,
                "updated_count": result.updated_count,
                "errors": result.errors,
            }
            for table_name, result in results.items()
        },
    }
