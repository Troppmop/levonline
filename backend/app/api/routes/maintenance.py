import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, SessionDep, StaffOrAdmin
from app.api.pagination import PaginationDep
from app.core.storage import save_damage_report_photo
from app.models.enums import MaintenanceStatus, ReportCategory, UserRole
from app.models.maintenance import DamageReport
from app.models.user import User
from app.schemas.maintenance import (
    DamageReportCreate,
    DamageReportRead,
    DamageReportStatusHistoryRead,
    DamageReportStatusUpdate,
    DamageReportUpdate,
)
from app.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


def _assert_owns_report(report: DamageReport, user: User) -> None:
    """A resident may only look at / attach photos to their own reports —
    UUIDs aren't guessable, but this closes the gap for shared links, logs,
    or a future listing endpoint that isn't as carefully scoped."""
    if user.role == UserRole.RESIDENT and report.resident_id != user.resident_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your report")


@router.get("/reports", response_model=list[DamageReportRead])
async def list_reports(
    session: SessionDep,
    current_user: CurrentUser,
    pagination: PaginationDep,
    status: MaintenanceStatus | None = None,
    room_id: uuid.UUID | None = None,
    category: ReportCategory | None = None,
):
    # Residents only ever see their own reports; staff/admin/av_bayit see
    # the building-wide list (optionally filtered by the params above).
    resident_id = current_user.resident_id if current_user.role == UserRole.RESIDENT else None
    return await MaintenanceService(session).list_filtered(
        status=status,
        room_id=room_id,
        category=category,
        resident_id=resident_id,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.post("/reports", response_model=DamageReportRead, status_code=201)
async def create_report(session: SessionDep, current_user: CurrentUser, payload: DamageReportCreate):
    # A resident can't file a report under someone else's name — force it
    # to their own profile regardless of what resident_id they sent.
    if current_user.role == UserRole.RESIDENT:
        payload = payload.model_copy(update={"resident_id": current_user.resident_id})
    return await MaintenanceService(session).create(payload, reported_by_id=current_user.id)


@router.get("/reports/{report_id}", response_model=DamageReportRead)
async def get_report(session: SessionDep, current_user: CurrentUser, report_id: uuid.UUID):
    report = await MaintenanceService(session).get(report_id)
    _assert_owns_report(report, current_user)
    return report


@router.patch("/reports/{report_id}", response_model=DamageReportRead)
async def update_report(
    session: SessionDep, _: StaffOrAdmin, report_id: uuid.UUID, payload: DamageReportUpdate
):
    return await MaintenanceService(session).update(report_id, payload)


@router.patch("/reports/{report_id}/status", response_model=DamageReportRead)
async def update_report_status(
    session: SessionDep, current_user: StaffOrAdmin, report_id: uuid.UUID, payload: DamageReportStatusUpdate
):
    return await MaintenanceService(session).transition_status(
        report_id, payload.status, payload.note, actor_id=current_user.id
    )


@router.get("/reports/{report_id}/history", response_model=list[DamageReportStatusHistoryRead])
async def report_history(session: SessionDep, current_user: CurrentUser, report_id: uuid.UUID):
    report = await MaintenanceService(session).get(report_id)
    _assert_owns_report(report, current_user)
    return report.status_history


@router.post("/reports/{report_id}/photos", response_model=DamageReportRead)
async def upload_photo(
    session: SessionDep, current_user: CurrentUser, report_id: uuid.UUID, file: UploadFile = File(...)
):
    service = MaintenanceService(session)
    report = await service.get(report_id)
    _assert_owns_report(report, current_user)
    url = await save_damage_report_photo(report_id, file)
    return await service.add_photos(report_id, [url])
