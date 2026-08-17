from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Lev LaChayal Residence Management"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://levlachayal:levlachayal@localhost:5432/levlachayal"

    # Redis / ARQ
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    # Kept as a plain string (not list[str]): pydantic-settings tries to
    # JSON-decode env values for list-typed fields before any validator
    # gets a chance to run, which crashes on a plain comma-separated value
    # like "http://a,http://b". cors_origins below does the real parsing.
    CORS_ORIGINS: str = "http://localhost:5173"

    # File uploads (damage report photos)
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Inventory
    LOW_STOCK_CHECK_CRON_MINUTE: int = 0  # top of every hour

    # Web push (VAPID). Generate a keypair with `vapid --gen` (installed
    # transitively via pywebpush's py_vapid dependency) or
    # `npx web-push generate-vapid-keys`. Left blank, push subscribe/
    # unsubscribe still works (so the frontend can register ahead of time)
    # but actually sending a notification is a no-op — see push_service.py.
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_CLAIMS_SUB: str = "mailto:admin@levlachayal.org"

    # Error tracking. Blank = Sentry never initializes (see core/sentry.py).
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def login_rate_limit(self) -> str:
        # E2E suites log in many times per run (once per role, per test) —
        # a strict per-minute cap that's appropriate against real brute
        # force attempts would make a full Playwright run flaky. Only test
        # mode gets the relaxed limit; production keeps the real one.
        return "1000/minute" if self.ENVIRONMENT == "test" else "5/minute"

    @property
    def refresh_rate_limit(self) -> str:
        return "1000/minute" if self.ENVIRONMENT == "test" else "20/minute"

    @property
    def registration_rate_limit(self) -> str:
        # Public, unauthenticated endpoint — needs its own cap against spam
        # signups, separate from login's. Relaxed in test mode like the
        # others, for the same reason (E2E suites submit repeatedly).
        return "1000/minute" if self.ENVIRONMENT == "test" else "5/hour"

    @property
    def sync_database_url(self) -> str:
        """Synchronous DSN for Alembic, which does not run under asyncio."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
