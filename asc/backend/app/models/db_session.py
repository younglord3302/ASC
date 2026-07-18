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
    """
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        future=True,
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
