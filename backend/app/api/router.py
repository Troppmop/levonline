from fastapi import APIRouter

from app.api.routes import (
    admin_data,
    announcements,
    auth,
    inventory,
    maintenance,
    meals,
    push,
    registration,
    residents,
    rooms,
    users,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(residents.router)
api_router.include_router(rooms.router)
api_router.include_router(inventory.router)
api_router.include_router(maintenance.router)
api_router.include_router(meals.router)
api_router.include_router(announcements.router)
api_router.include_router(registration.router)
api_router.include_router(push.router)
api_router.include_router(admin_data.router)
api_router.include_router(users.router)

if settings.ENVIRONMENT == "test":
    # Only mounted for E2E test runs; see app.api.routes.testing for why.
    from app.api.routes import testing

    api_router.include_router(testing.router)
