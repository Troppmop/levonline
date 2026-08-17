import logging

from app.core.config import settings

logger = logging.getLogger("app.sentry")


def init_sentry() -> None:
    """No-ops unless SENTRY_DSN is set, so local dev / CI never need a real
    DSN. Called once from both the API process (main.py) and the ARQ
    worker (worker.py) — each process needs its own init() call."""
    if not settings.SENTRY_DSN:
        return

    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    )
    logger.info("Sentry error tracking initialized (environment=%s)", settings.ENVIRONMENT)
