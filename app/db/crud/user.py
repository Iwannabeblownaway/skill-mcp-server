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
            "SELECT id, user_id, username, api_key, role, created_at FROM users WHERE api_key = %s",
            (api_key,),
        )
        return await cur.fetchone()


async def get_by_id(conn: aiomysql.Connection, user_id: int) -> Optional[dict]:
    """Get user by internal ID.

    Args:
        conn: Database connection
        user_id: Internal user ID (auto-increment)

    Returns:
        User dict or None if not found
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, user_id, username, api_key, role, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        return await cur.fetchone()


async def get_by_user_id(
    conn: aiomysql.Connection, user_id: str
) -> Optional[dict]:
    """Get user by user_id field.

    Args:
        conn: Database connection
        user_id: The user_id field value

    Returns:
        User dict or None if not found
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, user_id, username, api_key, role, created_at FROM users WHERE user_id = %s",
            (user_id,),
        )
        return await cur.fetchone()


async def create(
    conn: aiomysql.Connection,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    role: str = "user",
    api_key_length: int = 32,
) -> dict:
    """Create a new user with generated API key.

    Args:
        conn: Database connection
        user_id: User identifier (optional)
        username: Display name (optional)
        role: User role ('admin' or 'user')
        api_key_length: Length of generated API key

    Returns:
        Created user dict with generated api_key
    """
    api_key = secrets.token_urlsafe(api_key_length)

    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "INSERT INTO users (user_id, username, api_key, role) VALUES (%s, %s, %s, %s)",
            (user_id, username, api_key, role),
        )
        auto_id = cur.lastrowid

        return {
            "id": auto_id,
            "user_id": user_id,
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
            "SELECT id, user_id, username, api_key, role, created_at FROM users ORDER BY id LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return await cur.fetchall()


async def reset_api_key(
    conn: aiomysql.Connection,
    user_id: int,
    api_key_length: int = 32,
) -> Optional[dict]:
    """Reset user's API key to a new random key.

    Args:
        conn: Database connection
        user_id: Internal user ID (auto-increment)
        api_key_length: Length of new generated API key

    Returns:
        Updated user dict or None if user not found
    """
    new_api_key = secrets.token_urlsafe(api_key_length)

    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "UPDATE users SET api_key = %s WHERE id = %s",
            (new_api_key, user_id),
        )
        if cur.rowcount == 0:
            return None

        # Fetch and return the updated user
        await cur.execute(
            "SELECT id, user_id, username, api_key, role, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        return await cur.fetchone()


async def update(
    conn: aiomysql.Connection,
    user_id: int,
    username: Optional[str] = None,
    user_id_value: Optional[str] = None,
    role: Optional[str] = None,
) -> Optional[dict]:
    """Update user info (username, user_id field, and/or role).

    Args:
        conn: Database connection
        user_id: Internal user ID (auto-increment)
        username: New display name (optional, None means keep existing)
        user_id_value: New user_id field value (optional, "" means set to NULL)
        role: New role (optional, None means keep existing)

    Returns:
        Updated user dict or None if user not found
    """
    updates = []
    params = []

    if username is not None:
        updates.append("username = %s")
        params.append(username)
    if user_id_value is not None:
        updates.append("user_id = %s")
        params.append(user_id_value if user_id_value != "" else None)
    if role is not None:
        updates.append("role = %s")
        params.append(role)

    if not updates:
        return await get_by_id(conn, user_id)

    params.append(user_id)
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
            tuple(params),
        )
        if cur.rowcount == 0:
            return None

        # Fetch and return the updated user
        await cur.execute(
            "SELECT id, user_id, username, api_key, role, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        return await cur.fetchone()