import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.enums import ResidentStatus
from app.models.resident import Resident, ResidentActivityLog
from app.repositories.resident_repository import ResidentActivityLogRepository, ResidentRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.resident import ResidentCreate, ResidentOffboardRequest, ResidentUpdate


class ResidentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.residents = ResidentRepository(session)
        self.rooms = RoomRepository(session)
        self.activity_logs = ResidentActivityLogRepository(session)

    async def get(self, resident_id: uuid.UUID) -> Resident:
        resident = await self.residents.get_with_room(resident_id)
        if not resident:
            raise NotFoundError("Resident not found")
        return resident

    async def list_residents(
        self, offset: int = 0, limit: int = 100, assigned_av_bayit_id=None, archived: bool = False
    ):
        return await self.residents.list_with_room(
            offset=offset,
            limit=limit,
            is_active=None,
            is_archived=archived,
            assigned_av_bayit_id=assigned_av_bayit_id,
        )

    async def list_by_room_layout(self):
        """Feeds the presence tracker: rooms ordered by floor/position, each
        with its residents, so the UI can render Home/Away by physical
        layout rather than an alphabetical resident list."""
        return await self.rooms.list_with_residents()

    async def create(self, data: ResidentCreate, actor_id: uuid.UUID | None = None) -> Resident:
        resident = Resident(**data.model_dump())
        resident = await self.residents.create(resident)
        await self._log_activity(resident.id, "created", "Resident profile created", actor_id)
        return await self.get(resident.id)

    async def update(
        self, resident_id: uuid.UUID, data: ResidentUpdate, actor_id: uuid.UUID | None = None
    ) -> Resident:
        resident = await self.residents.get(resident_id)
        if not resident:
            raise NotFoundError("Resident not found")

        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return await self.get(resident_id)

        await self.residents.update(resident, changes)

        if "status" in changes:
            await self._log_activity(
                resident_id, "status_change", f"Status changed to {changes['status']}", actor_id
            )
        other_changes = {k: v for k, v in changes.items() if k != "status"}
        if other_changes:
            fields = ", ".join(other_changes.keys())
            await self._log_activity(resident_id, "profile_update", f"Updated fields: {fields}", actor_id)

        return await self.get(resident_id)

    async def set_status(
        self, resident_id: uuid.UUID, status: ResidentStatus, actor_id: uuid.UUID | None = None
    ) -> Resident:
        resident = await self.residents.get(resident_id)
        if not resident:
            raise NotFoundError("Resident not found")
        await self.residents.update(resident, {"status": status})
        await self._log_activity(resident_id, "status_change", f"Status changed to {status.value}", actor_id)
        return await self.get(resident_id)

    async def offboard(
        self,
        resident_id: uuid.UUID,
        checklist: ResidentOffboardRequest,
        actor_id: uuid.UUID | None = None,
    ) -> Resident:
        resident = await self.residents.get(resident_id)
        if not resident:
            raise NotFoundError("Resident not found")
        await self.residents.update(resident, {"is_active": False, "is_archived": True})

        items = [
            ("Room key returned" if checklist.key_returned else "Room key NOT returned"),
            ("Biometric access cleared" if checklist.biometric_cleared else "Biometric access NOT cleared"),
            ("Deposit/rent balance settled" if checklist.balance_settled else "Deposit/rent balance NOT settled"),
        ]
        description = "Resident offboarded. " + "; ".join(items) + "."
        if checklist.note:
            description += f" Note: {checklist.note}"
        await self._log_activity(resident_id, "offboarded", description, actor_id)
        return await self.get(resident_id)

    async def list_activity(self, resident_id: uuid.UUID):
        return await self.activity_logs.list_for_resident(resident_id)

    async def _log_activity(
        self, resident_id: uuid.UUID, activity_type: str, description: str, actor_id: uuid.UUID | None
    ) -> None:
        log = ResidentActivityLog(
            resident_id=resident_id,
            activity_type=activity_type,
            description=description,
            created_by_id=actor_id,
        )
        await self.activity_logs.create(log)
