from sqlalchemy import select

from app.models.enums import RegistrationStatus
from app.models.registration import ResidentRegistrationRequest
from app.repositories.base import BaseRepository


class RegistrationRequestRepository(BaseRepository[ResidentRegistrationRequest]):
    model = ResidentRegistrationRequest

    async def has_open_request(self, email: str) -> bool:
        """True if this email already has a pending or approved request —
        used to block duplicate submissions without blocking someone from
        trying again after a rejection."""
        stmt = select(ResidentRegistrationRequest).where(
            ResidentRegistrationRequest.email == email,
            ResidentRegistrationRequest.status.in_(
                [RegistrationStatus.PENDING, RegistrationStatus.APPROVED]
            ),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_by_status(self, status: RegistrationStatus | None, offset: int = 0, limit: int = 200):
        stmt = select(ResidentRegistrationRequest)
        if status is not None:
            stmt = stmt.where(ResidentRegistrationRequest.status == status)
        stmt = stmt.order_by(ResidentRegistrationRequest.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def latest_for_email(self, email: str) -> ResidentRegistrationRequest | None:
        stmt = (
            select(ResidentRegistrationRequest)
            .where(ResidentRegistrationRequest.email == email)
            .order_by(ResidentRegistrationRequest.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
