"""Async SQLAlchemy database helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from pio_lab.memory.postgres.models import Base
from pio_lab.utils.env import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def build_database_url() -> str:
    """Build the default database URL from settings."""
    return get_settings().postgres_dsn


def init_engine(database_url: str | None = None, echo: bool = False) -> AsyncEngine:
    """Initialize and cache the async engine."""
    global _engine, _session_factory

    _engine = create_async_engine(database_url or build_database_url(), echo=echo, future=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_engine() -> AsyncEngine:
    """Return the cached engine, creating it on first use."""
    if _engine is None:
        return init_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the cached async session factory."""
    global _session_factory

    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def create_all(engine: AsyncEngine | None = None) -> None:
    """Create all memory tables."""
    selected_engine = engine or get_engine()
    async with selected_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all(engine: AsyncEngine | None = None) -> None:
    """Drop all memory tables."""
    selected_engine = engine or get_engine()
    async with selected_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def dispose_engine() -> None:
    """Dispose the cached engine."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


__all__ = [
    "build_database_url",
    "create_all",
    "dispose_engine",
    "drop_all",
    "get_engine",
    "get_session",
    "get_session_factory",
    "init_engine",
]
