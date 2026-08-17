import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import MealInvitationStatus
from app.models.meal import MealHostingRecord, MealInvitation
from app.repositories.meal_repository import MealHostingRepository, MealInvitationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.meal import MealHostingRecordCreate, MealHostingSummary, MealInvitationCreate
from app.services.push_service import send_notification_to_user


class MealService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.hosting = MealHostingRepository(session)
        self.invitations = MealInvitationRepository(session)
        self.users = UserRepository(session)

    async def create(
        self, data: MealHostingRecordCreate, host_user_id: uuid.UUID | None = None
    ) -> MealHostingRecord:
        record = MealHostingRecord(**data.model_dump(), host_user_id=host_user_id)
        return await self.hosting.create(record)

    async def list_filtered(
        self,
        host_family_name: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int = 100,
    ):
        return await self.hosting.list_filtered(
            host_family_name=host_family_name,
            date_from=date_from,
            date_to=date_to,
            offset=offset,
            limit=limit,
        )

    async def hosting_summary(
        self, date_from: date | None = None, date_to: date | None = None
    ) -> list[MealHostingSummary]:
        rows = await self.hosting.hosting_summary(date_from=date_from, date_to=date_to)
        return [
            MealHostingSummary(
                host_family_name=row.host_family_name,
                total_meals_hosted=row.total_meals_hosted,
                total_guests_hosted=int(row.total_guests_hosted),
            )
            for row in rows
        ]

    # --- meal invitations (forward-looking RSVP flow) ---

    async def create_invitation(self, data: MealInvitationCreate, host_user_id: uuid.UUID) -> MealInvitation:
        invitation = MealInvitation(**data.model_dump(), host_user_id=host_user_id)
        invitation = await self.invitations.create(invitation)

        resident_user = await self.users.get_by_resident_id(invitation.resident_id)
        if resident_user:
            await send_notification_to_user(
                self.session,
                resident_user.id,
                "Meal Invitation",
                f"{invitation.host_family_name} invited you for {invitation.meal_type.value}",
                url="/r/meals",
            )

        return invitation

    async def list_invitations_for_resident(self, resident_id: uuid.UUID):
        return await self.invitations.list_for_resident(resident_id)

    async def list_invitations_for_host(self, host_user_id: uuid.UUID):
        return await self.invitations.list_for_host(host_user_id)

    async def get_invitation(self, invitation_id: uuid.UUID) -> MealInvitation:
        invitation = await self.invitations.get(invitation_id)
        if not invitation:
            raise NotFoundError("Meal invitation not found")
        return invitation

    async def respond_to_invitation(
        self, invitation_id: uuid.UUID, new_status: MealInvitationStatus
    ) -> MealInvitation:
        invitation = await self.get_invitation(invitation_id)
        if invitation.status != MealInvitationStatus.PENDING:
            raise ValidationError(f"Invitation already {invitation.status.value}")
        invitation = await self.invitations.update(invitation, {"status": new_status})

        await send_notification_to_user(
            self.session,
            invitation.host_user_id,
            "Meal Invitation Response",
            f"Your invitation for {invitation.meal_date} was {new_status.value}",
            url="/meals",
        )

        return invitation
