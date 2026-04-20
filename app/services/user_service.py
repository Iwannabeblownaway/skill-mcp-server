"""User service - business logic for user operations."""

from typing import Optional

from app.db.session import get_db
from app.db.crud import user as user_crud


async def verify_api_key(api_key: str) -> Optional[dict]:
    """Verify an API key and return the associated user.

    Args:
        api_key: API key to verify

    Returns:
        User dict if valid, None otherwise
    """
    async with get_db() as conn:
        return await user_crud.get_by_api_key(conn, api_key)


async def create_user(user_id: str, username: str, role: str = "user") -> dict:
    """Create a new user with generated API key.

    Args:
        user_id: Unique user identifier
        username: User display name
        role: User role ('admin' or 'user')

    Returns:
        User dict with generated api_key
    """
    async with get_db() as conn:
        return await user_crud.create(
            conn, external_id=user_id, username=username, role=role
        )


async def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get a user by ID.

    Args:
        user_id: User ID

    Returns:
        User dict or None if not found
    """
    async with get_db() as conn:
        return await user_crud.get_by_id(conn, user_id)
