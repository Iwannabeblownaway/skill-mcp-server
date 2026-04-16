"""User CRUD operations."""

from typing import Optional
import secrets

import aiomysql


async def get_by_api_key(conn: aiomysql.Connection, api_key: str) -> Optional[dict]:
    """Get user by API key.

    Args:
        conn: Database connection
        api_key: User's API key

    Returns:
        User dict or None if not found
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, external_id, username, api_key, role, created_at FROM users WHERE api_key = %s",
            (api_key,),
        )
        return await cur.fetchone()


async def get_by_id(conn: aiomysql.Connection, user_id: int) -> Optional[dict]:
    """Get user by internal ID.

    Args:
        conn: Database connection
        user_id: Internal user ID

    Returns:
        User dict or None if not found
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, external_id, username, api_key, role, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        return await cur.fetchone()


async def get_by_external_id(
    conn: aiomysql.Connection, external_id: str
) -> Optional[dict]:
    """Get user by external ID.

    Args:
        conn: Database connection
        external_id: External system ID

    Returns:
        User dict or None if not found
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, external_id, username, api_key, role, created_at FROM users WHERE external_id = %s",
            (external_id,),
        )
        return await cur.fetchone()


async def create(
    conn: aiomysql.Connection,
    external_id: Optional[str] = None,
    username: Optional[str] = None,
    role: str = "user",
    api_key_length: int = 32,
) -> dict:
    """Create a new user.

    Args:
        conn: Database connection
        external_id: External system ID (optional)
        username: Display name (optional)
        role: User role ('admin' or 'user')
        api_key_length: Length of generated API key

    Returns:
        Created user dict with generated api_key
    """
    api_key = secrets.token_urlsafe(api_key_length)

    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "INSERT INTO users (external_id, username, api_key, role) VALUES (%s, %s, %s, %s)",
            (external_id, username, api_key, role),
        )
        user_id = cur.lastrowid

        return {
            "id": user_id,
            "external_id": external_id,
            "username": username,
            "api_key": api_key,
            "role": role,
        }


async def list_users(
    conn: aiomysql.Connection, limit: int = 100, offset: int = 0
) -> list[dict]:
    """List all users.

    Args:
        conn: Database connection
        limit: Maximum number of users to return
        offset: Number of users to skip

    Returns:
        List of user dicts
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, external_id, username, api_key, role, created_at FROM users ORDER BY id LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return await cur.fetchall()
