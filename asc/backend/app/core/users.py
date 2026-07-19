"""User account storage with a database-first, in-memory-fallback strategy.

When Postgres is reachable, users are persisted to the ``users`` table and are
durable/shared across processes. When it is not (local dev, tests), an
in-process dict keeps auth working. This mirrors the best-effort philosophy of
the rest of the persistence layer.
"""

import asyncio
import logging
import uuid
from typing import Optional

from sqlalchemy import select

from app.core.security import get_password_hash, verify_password
from app.models.db_session import SessionLocal
from app.models.database import UserModel

logger = logging.getLogger("asc.users")

# In-memory fallback store: email -> record dict
_memory_users: dict[str, dict] = {}

# Once a DB connection attempt fails we stop trying for the lifetime of the
# process. This mirrors app.models.persistence: a slow/unreachable Postgres must
# never block auth endpoints (register/login/me) on the same event loop.
_db_disabled = False
_DB_TIMEOUT = 3.0


async def _safe_db(make_coro):
    """Run a DB coroutine (built lazily) with a timeout, returning its value or
    ``_SENTINEL`` if it failed/timed out. After the first failure, DB access is
    disabled entirely so subsequent calls fall straight through to memory. The
    coroutine is built lazily so a disabled DB doesn't leave an unawaited
    coroutine behind."""
    global _db_disabled
    if _db_disabled:
        return _SENTINEL
    try:
        return await asyncio.wait_for(make_coro(), timeout=_DB_TIMEOUT)
    except Exception as exc:  # noqa: BLE001 - fall back to in-memory users
        _db_disabled = True
        logger.debug("user DB access disabled (database unavailable): %s", exc)
        return _SENTINEL


class _Sentinel:
    pass


_SENTINEL = _Sentinel()


def _to_dict(user: UserModel) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "hashed_password": user.hashed_password,
        "full_name": user.full_name,
        "is_active": user.is_active,
    }


async def get_user_by_email(email: str) -> Optional[dict]:
    """Return the user record for an email, or None. Tries DB, then memory."""
    async def _q():
        async with SessionLocal() as session:
            row = (
                await session.execute(
                    select(UserModel).where(UserModel.email == email)
                )
            ).scalar_one_or_none()
            return _to_dict(row) if row is not None else _SENTINEL

    result = await _safe_db(_q)
    if result is not _SENTINEL:
        return result
    return _memory_users.get(email)


async def create_user(email: str, password: str, full_name: Optional[str] = None) -> dict:
    """Create a new user. Raises ValueError if the email already exists."""
    existing = await get_user_by_email(email)
    if existing is not None:
        raise ValueError("A user with this email already exists")

    record = {
        "id": str(uuid.uuid4()),
        "email": email,
        "hashed_password": get_password_hash(password),
        "full_name": full_name,
        "is_active": True,
    }

    async def _insert():
        async with SessionLocal() as session:
            session.add(
                UserModel(
                    id=record["id"],
                    email=record["email"],
                    hashed_password=record["hashed_password"],
                    full_name=record["full_name"],
                    is_active=record["is_active"],
                )
            )
            await session.commit()

    # A failure here is swallowed by _safe_db; we then keep the user in memory.
    await _safe_db(_insert)
    if email not in _memory_users:
        _memory_users[email] = record
    return record


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Return the user record if credentials are valid, else None."""
    user = await get_user_by_email(email)
    if user is None:
        return None
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user
