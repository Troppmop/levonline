"""Verifies the core promise from the spec: every DB write goes through a
session whose commit/rollback is handled centrally, so a failure partway
through a unit of work never leaves partial writes behind.

This exercises the real app.core.db.session_scope (the same contract
get_session uses for HTTP requests) against a throwaway SQLite engine.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select

import app.core.db as db_module
from app.models.room import Room


@pytest.mark.asyncio
async def test_session_scope_rolls_back_on_exception(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "async_session_factory", factory)

    with pytest.raises(RuntimeError):
        async with db_module.session_scope() as session:
            session.add(Room(floor=1, room_number="999"))
            await session.flush()  # the write is visible mid-transaction...
            raise RuntimeError("simulated failure after a successful write")

    # ...but must not have survived the rollback.
    async with factory() as verify_session:
        result = await verify_session.execute(select(Room).where(Room.room_number == "999"))
        assert result.scalar_one_or_none() is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_session_scope_commits_on_success(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "async_session_factory", factory)

    async with db_module.session_scope() as session:
        session.add(Room(floor=2, room_number="200"))

    async with factory() as verify_session:
        result = await verify_session.execute(select(Room).where(Room.room_number == "200"))
        assert result.scalar_one_or_none() is not None

    await engine.dispose()
