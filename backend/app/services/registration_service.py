import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.enums import RegistrationStatus, ResidentStatus, UserRole
from app.models.registration import ResidentRegistrationRequest
from app.models.resident import Resident, ResidentActivityLog
from app.models.user import User
from app.repositories.registration_repository import RegistrationRequestRepository
from app.repositories.resident_repository import ResidentActivityLogRepository, ResidentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.registration import RegistrationRequestCreate
from app.services.push_service import send_notification_to_user


class RegistrationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.requests = RegistrationRequestRepository(session)
        self.residents = ResidentRepository(session)
        self.users = UserRepository(session)
        self.activity_logs = ResidentActivityLogRepository(session)

    async def submit(self, data: RegistrationRequestCreate) -> ResidentRegistrationRequest:
        if await self.users.get_by_email(data.email):
            raise ConflictError("An account with this email already exists — try logging in instead")
        if await self.requests.has_open_request(data.email):
            raise ConflictError("A registration request for this email is already pending review")

        request = ResidentRegistrationRequest(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            hashed_password=hash_password(data.password),
        )
        request = await self.requests.create(request)

        recipients = await self.users.list_active_by_roles(UserRole.STAFF, UserRole.ADMIN)
        for user in recipients:
            await send_notification_to_user(
                self.session,
                user.id,
                "New Registration Request",
                f"{request.first_name} {request.last_name} applied to join",
                url="/registrations",
            )

        return request

    async def get(self, request_id: uuid.UUID) -> ResidentRegistrationRequest:
        request = await self.requests.get(request_id)
        if not request:
            raise NotFoundError("Registration request not found")
        return request

    async def list_requests(self, status: RegistrationStatus | None = None):
        return await self.requests.list_by_status(status)

    async def approve(
        self, request_id: uuid.UUID, reviewer_id: uuid.UUID, room_id: uuid.UUID | None = None
    ) -> Resident:
        request = await self.get(request_id)
        if request.status != RegistrationStatus.PENDING:
            raise ValidationError(f"Request already {request.status.value}")

        resident = Resident(
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
            email=request.email,
            room_id=room_id,
            status=ResidentStatus.HOME,
        )
        resident = await self.residents.create(resident)

        user = User(
            email=request.email,
            hashed_password=request.hashed_password,
            full_name=f"{request.first_name} {request.last_name}",
            role=UserRole.RESIDENT,
            resident_id=resident.id,
        )
        await self.users.create(user)

        await self.activity_logs.create(
            ResidentActivityLog(
                resident_id=resident.id,
                activity_type="created",
                description="Resident profile and login created via self-registration approval",
                created_by_id=reviewer_id,
            )
        )

        await self.requests.update(
            request,
            {
                "status": RegistrationStatus.APPROVED,
                "reviewed_by_id": reviewer_id,
                "reviewed_at": datetime.now(UTC),
                "created_resident_id": resident.id,
            },
        )

        return await self.residents.get_with_room(resident.id)

    async def reject(
        self, request_id: uuid.UUID, reviewer_id: uuid.UUID, note: str | None = None
    ) -> ResidentRegistrationRequest:
        request = await self.get(request_id)
        if request.status != RegistrationStatus.PENDING:
            raise ValidationError(f"Request already {request.status.value}")

        return await self.requests.update(
            request,
            {
                "status": RegistrationStatus.REJECTED,
                "reviewed_by_id": reviewer_id,
                "reviewed_at": datetime.now(UTC),
                "review_note": note,
            },
        )
