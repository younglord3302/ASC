"""User account storage with a database-first, in-memory-fallback strategy.

When Postgres is reachable, users are persisted to the ``users`` table and are
durable/shared across processes. When it is not (local dev, tests), an
in-process dict keeps auth working. This mirrors the best-effort philosophy of
the rest of the persistence layer.
"""

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
    try:
        async with SessionLocal() as session:
            row = (
                await session.execute(
                    select(UserModel).where(UserModel.email == email)
                )
            ).scalar_one_or_none()
            if row is not None:
                return _to_dict(row)
    except Exception as exc:  # noqa: BLE001 - fall back to memory
        logger.debug("get_user_by_email DB lookup failed, using memory: %s", exc)
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

    persisted = False
    try:
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
            persisted = True
    except Exception as exc:  # noqa: BLE001 - fall back to memory
        logger.debug("create_user DB write failed, using memory: %s", exc)

    if not persisted:
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
