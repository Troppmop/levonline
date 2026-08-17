import os

# Must be set before any `app.*` module is imported: app.core.config.settings
# is a module-level singleton, and ENVIRONMENT=test switches the rate
# limiter to in-memory storage (no Redis in the test environment) and skips
# mounting the destructive /testing/reset endpoint outside of E2E runs.
os.environ["ENVIRONMENT"] = "test"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registers table metadata)
from app.core.db import get_session
from app.core.rate_limit import limiter
from app.main import app as fastapi_app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The limiter's in-memory storage is a module-level singleton that
    otherwise persists across the whole test session, so login/refresh
    calls in one test would count against the next test's rate limit."""
    limiter.reset()
    yield
    limiter.reset()


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Isolated in-memory DB per test so tests never share state."""
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as s:
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncClient:
    async def override_get_session():
        # Mirrors app.core.db.get_session's commit/rollback contract exactly
        # (rather than just yielding the raw session) so tests exercise the
        # same rollback-on-exception behavior requests get in production.
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    fastapi_app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    fastapi_app.dependency_overrides.clear()


ADMIN_EMAIL = "admin@lev.org"
ADMIN_PASSWORD = "password123"


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, session: AsyncSession) -> dict[str, str]:
    """Seeds an admin user directly (bypassing the register-requires-admin
    chicken/egg problem) and returns Authorization headers for it."""
    from app.core.security import hash_password
    from app.models.enums import UserRole
    from app.models.user import User

    session.add(
        User(
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Admin",
            role=UserRole.ADMIN,
        )
    )
    await session.commit()

    login = await client.post(
        "/api/v1/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def make_login(client: AsyncClient, session: AsyncSession):
    """Factory fixture: make_login(email, password, role, resident_id=None)
    seeds a User directly and returns Authorization headers for it —
    bypassing the admin-gated /auth/register endpoint for test setup."""
    import uuid

    from app.core.security import hash_password
    from app.models.user import User

    async def _make(email: str, password: str, role, resident_id=None) -> dict[str, str]:
        if isinstance(resident_id, str):
            resident_id = uuid.UUID(resident_id)
        session.add(
            User(
                email=email,
                hashed_password=hash_password(password),
                full_name=email.split("@")[0],
                role=role,
                resident_id=resident_id,
            )
        )
        await session.commit()
        login = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    return _make
