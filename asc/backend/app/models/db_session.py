"""Async SQLAlchemy engine, session factory, and DB initialization."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.database import Base


def _make_engine() -> AsyncEngine:
    """Create the async engine from the configured DATABASE_URL.

    The URL is expected to use an async driver (e.g. ``postgresql+asyncpg://``).

    A short asyncpg connection timeout is configured so that an unreachable
    database fails fast instead of hanging the event loop (which would otherwise
    stall the entire workflow pipeline, since persistence is best-effort).
    """
    connect_args = {"timeout": 3, "server_settings": {"application_name": "asc"}}
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        future=True,
        pool_timeout=3,
        connect_args=connect_args,
    )


engine: AsyncEngine = _make_engine()

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Create all tables if they do not exist.

    For real migrations use Alembic; this is a convenience for local/dev and
    first-run bootstrapping.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional async session scope."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
