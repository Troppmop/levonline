import logging
from datetime import date

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.db import session_scope
from app.core.logging import configure_logging
from app.core.sentry import init_sentry
from app.models.enums import UserRole
from app.repositories.inventory_repository import InventoryItemRepository
from app.repositories.meal_repository import MealHostingRepository
from app.repositories.user_repository import UserRepository
from app.services.push_service import send_notification_to_user

configure_logging()
logger = logging.getLogger("arq.worker")


async def check_low_stock(ctx) -> dict:
    """Scans inventory and push-notifies staff/admin about items at/below
    their low-stock threshold (in addition to the existing log line)."""
    async with session_scope() as session:
        items = await InventoryItemRepository(session).list_low_stock()
        for item in items:
            await _notify(
                f"LOW STOCK: {item.name} at {item.location.value} "
                f"({item.quantity} {item.unit} <= threshold {item.low_stock_threshold})"
            )

        if items:
            recipients = await UserRepository(session).list_active_by_roles(UserRole.STAFF, UserRole.ADMIN)
            body = (
                f"{items[0].name} is low"
                if len(items) == 1
                else f"{len(items)} inventory items are low on stock"
            )
            for user in recipients:
                await send_notification_to_user(
                    session, user.id, "Low Stock Alert", body, url="/inventory"
                )

        return {"low_stock_count": len(items)}


async def send_meal_reminder(ctx) -> dict:
    """Reminds Av/Eim Bayit families who haven't logged a hosting record
    for the upcoming Shabbat to submit one."""
    async with session_scope() as session:
        records = await MealHostingRepository(session).list_filtered(
            date_from=date.today(), date_to=date.today()
        )
        await _notify(f"Meal reminder run: {len(records)} hosting records already logged for today")

        recipients = await UserRepository(session).list_active_by_roles(UserRole.AV_BAYIT)
        for user in recipients:
            await send_notification_to_user(
                session,
                user.id,
                "Meal Hosting Reminder",
                "Don't forget to log or plan today's meal hosting.",
                url="/meals",
            )

        return {"records_today": len(records)}


async def _notify(message: str) -> None:
    logger.info(message)


async def startup(ctx) -> None:
    init_sentry()
    logger.info("ARQ worker starting up")


async def shutdown(ctx) -> None:
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    functions = [check_low_stock, send_meal_reminder]
    cron_jobs = [
        # Hourly low-stock sweep.
        cron(check_low_stock, minute=settings.LOW_STOCK_CHECK_CRON_MINUTE),
        # Daily meal-reminder nudge at 15:00 UTC.
        cron(send_meal_reminder, hour=15, minute=0),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
