"""All SQLModel table models, imported here so Alembic's autogenerate (via
app.core.db metadata) can discover every table with a single import."""

from app.models.announcement import Announcement
from app.models.inventory import InventoryItem, InventoryTransaction
from app.models.maintenance import DamageReport, DamageReportStatusHistory
from app.models.meal import MealHostingRecord, MealInvitation
from app.models.push_subscription import PushSubscription
from app.models.refresh_token import RefreshToken
from app.models.registration import ResidentRegistrationRequest
from app.models.resident import Resident, ResidentActivityLog
from app.models.room import Room
from app.models.user import User

__all__ = [
    "Announcement",
    "InventoryItem",
    "InventoryTransaction",
    "DamageReport",
    "DamageReportStatusHistory",
    "MealHostingRecord",
    "MealInvitation",
    "PushSubscription",
    "RefreshToken",
    "ResidentRegistrationRequest",
    "Resident",
    "ResidentActivityLog",
    "Room",
    "User",
]
