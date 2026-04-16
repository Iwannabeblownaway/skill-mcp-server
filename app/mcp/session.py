"""MCP session management module with Redis storage.

This module provides session management for MCP connections,
storing user context and session state in Redis.
"""

import uuid
from typing import Optional
from datetime import datetime

from app.utils.redis_client import redis_client


# Default session TTL in seconds (24 hours)
DEFAULT_SESSION_TTL = 86400

# Session key prefix in Redis
SESSION_KEY_PREFIX = "mcp:session:"


def generate_session_id() -> str:
    """Generate a unique session ID.

    Returns:
        A unique UUID string for the session.
    """
    return str(uuid.uuid4())


async def create_session(user_id: int, username: str, user_role: str) -> str:
    """Create a new MCP session for a user.

    Args:
        user_id: The user's unique identifier.
        username: The user's display name.
        user_role: The user's role (e.g., 'admin', 'user').

    Returns:
        The newly generated session ID.
    """
    session_id = generate_session_id()

    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "username": username,
        "user_role": user_role,
        "created_at": datetime.utcnow().isoformat(),
        "last_activity": datetime.utcnow().isoformat(),
    }

    await redis_client.put_session(
        f"{SESSION_KEY_PREFIX}{session_id}",
        session_data,
        ttl=DEFAULT_SESSION_TTL,
    )

    return session_id


async def get_session(session_id: str) -> Optional[dict]:
    """Retrieve session data by session ID.

    Args:
        session_id: The session identifier.

    Returns:
        Session data dictionary if found, None otherwise.
    """
    if not session_id:
        return None

    session_data = await redis_client.get_session(f"{SESSION_KEY_PREFIX}{session_id}")

    return session_data


async def update_session_activity(session_id: str) -> bool:
    """Update the last activity timestamp for a session.

    Args:
        session_id: The session identifier.

    Returns:
        True if session was updated, False if not found.
    """
    session_data = await get_session(session_id)

    if session_data is None:
        return False

    session_data["last_activity"] = datetime.utcnow().isoformat()

    await redis_client.put_session(
        f"{SESSION_KEY_PREFIX}{session_id}",
        session_data,
        ttl=DEFAULT_SESSION_TTL,
    )

    return True


async def delete_session(session_id: str) -> bool:
    """Delete a session from Redis.

    Args:
        session_id: The session identifier.

    Returns:
        True if session was deleted, False if not found.
    """
    if not session_id:
        return False

    await redis_client.delete_session(f"{SESSION_KEY_PREFIX}{session_id}")
    return True


async def get_user_id_from_session(session_id: str) -> Optional[int]:
    """Extract user_id from a session.

    Args:
        session_id: The session identifier.

    Returns:
        The user_id if session exists, None otherwise.
    """
    session_data = await get_session(session_id)

    if session_data is None:
        return None

    return session_data.get("user_id")


async def validate_session(session_id: str) -> Optional[dict]:
    """Validate and return session data.

    Also updates the last activity timestamp if session is valid.

    Args:
        session_id: The session identifier.

    Returns:
        Session data if valid, None otherwise.
    """
    session_data = await get_session(session_id)

    if session_data is None:
        return None

    # Update last activity
    await update_session_activity(session_id)

    return session_data
