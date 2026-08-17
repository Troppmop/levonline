from datetime import date

from sqlalchemy import func, select

from app.models.meal import MealHostingRecord, MealInvitation
from app.repositories.base import BaseRepository


class MealHostingRepository(BaseRepository[MealHostingRecord]):
    model = MealHostingRecord

    async def list_filtered(
        self,
        host_family_name: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int = 200,
    ):
        stmt = select(MealHostingRecord)
        if host_family_name is not None:
            stmt = stmt.where(MealHostingRecord.host_family_name == host_family_name)
        if date_from is not None:
            stmt = stmt.where(MealHostingRecord.meal_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(MealHostingRecord.meal_date <= date_to)
        stmt = stmt.order_by(MealHostingRecord.meal_date.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def hosting_summary(self, date_from: date | None = None, date_to: date | None = None):
        stmt = select(
            MealHostingRecord.host_family_name,
            func.count(MealHostingRecord.id).label("total_meals_hosted"),
            func.coalesce(func.sum(MealHostingRecord.guest_count), 0).label("total_guests_hosted"),
        ).group_by(MealHostingRecord.host_family_name)
        if date_from is not None:
            stmt = stmt.where(MealHostingRecord.meal_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(MealHostingRecord.meal_date <= date_to)
        stmt = stmt.order_by(func.count(MealHostingRecord.id).desc())
        result = await self.session.execute(stmt)
        return result.all()


class MealInvitationRepository(BaseRepository[MealInvitation]):
    model = MealInvitation

    async def list_for_resident(self, resident_id, offset: int = 0, limit: int = 100):
        stmt = (
            select(MealInvitation)
            .where(MealInvitation.resident_id == resident_id)
            .order_by(MealInvitation.meal_date.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_for_host(self, host_user_id, offset: int = 0, limit: int = 100):
        stmt = (
            select(MealInvitation)
            .where(MealInvitation.host_user_id == host_user_id)
            .order_by(MealInvitation.meal_date.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
