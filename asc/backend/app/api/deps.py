"""Shared FastAPI dependencies (authentication)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token
from app.core.users import get_user_by_email
from app.models.schemas import UserResponse

# tokenUrl points at the login endpoint (for OpenAPI/Swagger "Authorize").
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """Resolve and validate the current user from a bearer JWT."""
    payload = decode_access_token(token)
    if not payload:
        raise _credentials_exc
    email = payload.get("sub")
    if not email:
        raise _credentials_exc
    user = await get_user_by_email(email)
    if user is None:
        raise _credentials_exc
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name"),
        is_active=user.get("is_active", True),
    )
