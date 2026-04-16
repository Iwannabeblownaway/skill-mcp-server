"""API dependencies for authentication and database access."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Header, status

from app.db.session import get_db
from app.db.crud import user as user_crud


async def get_current_user(
    x_api_key: Annotated[str, Header(..., description="API Key for authentication")],
) -> dict:
    """Get current user from X-API-Key header."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    async with get_db() as conn:
        user = await user_crud.get_by_api_key(conn, x_api_key)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return user


async def verify_admin_api_key(
    x_api_key: Annotated[str, Header(..., description="API Key for authentication")],
) -> dict:
    """Verify API key and ensure user has admin role."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    async with get_db() as conn:
        user = await user_crud.get_by_api_key(conn, x_api_key)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return user
