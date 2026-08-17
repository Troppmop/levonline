"""Test-only endpoint that resets the database to a clean, seeded state.

Only mounted when ENVIRONMENT=test (see app.main), so it can never be hit in
staging/production. Playwright's global setup calls this before the suite
runs, and optionally between test files, to guarantee isolated, repeatable
E2E runs instead of accumulating state across tests.
"""
from fastapi import APIRouter
from sqlmodel import SQLModel

from app.core.db import engine, session_scope
from app.core.security import hash_password
from app.models.announcement import Announcement
from app.models.enums import UserRole
from app.models.resident import Resident
from app.models.room import Room
from app.models.user import User

router = APIRouter(prefix="/testing", tags=["testing"])

TEST_ADMIN_EMAIL = "e2e-admin@lev.org"
TEST_ADMIN_PASSWORD = "e2e-test-password"
TEST_AV_BAYIT_EMAIL = "e2e-avbayit@lev.org"
TEST_AV_BAYIT_PASSWORD = "e2e-test-password"
TEST_RESIDENT_EMAIL = "e2e-resident@lev.org"
TEST_RESIDENT_PASSWORD = "e2e-test-password"


@router.post("/reset")
async def reset_database() -> dict:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    async with session_scope() as session:
        session.add(
            User(
                email=TEST_ADMIN_EMAIL,
                hashed_password=hash_password(TEST_ADMIN_PASSWORD),
                full_name="E2E Admin",
                role=UserRole.ADMIN,
            )
        )
        av_bayit_user = User(
            email=TEST_AV_BAYIT_EMAIL,
            hashed_password=hash_password(TEST_AV_BAYIT_PASSWORD),
            full_name="E2E Host Family",
            role=UserRole.AV_BAYIT,
        )
        session.add(av_bayit_user)

        rooms = [
            Room(floor=1, room_number="101", display_order=1),
            Room(floor=1, room_number="102", display_order=2),
            Room(floor=2, room_number="201", display_order=1),
        ]
        session.add_all(rooms)
        await session.flush()  # need generated IDs for the FKs below

        resident = Resident(
            first_name="E2E",
            last_name="Resident",
            room_id=rooms[0].id,
            assigned_av_bayit_id=av_bayit_user.id,
        )
        session.add(resident)
        await session.flush()

        session.add(
            User(
                email=TEST_RESIDENT_EMAIL,
                hashed_password=hash_password(TEST_RESIDENT_PASSWORD),
                full_name="E2E Resident",
                role=UserRole.RESIDENT,
                resident_id=resident.id,
            )
        )
        session.add(
            Announcement(title="Welcome", body="House meeting tonight at 8pm.", created_by_id=None)
        )

    return {
        "status": "reset",
        "admin_email": TEST_ADMIN_EMAIL,
        "av_bayit_email": TEST_AV_BAYIT_EMAIL,
        "resident_email": TEST_RESIDENT_EMAIL,
    }
