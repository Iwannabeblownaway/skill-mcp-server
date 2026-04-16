"""Skill call log CRUD operations."""

from typing import Optional

import aiomysql


async def create_log(
    conn: aiomysql.Connection,
    user_id: int,
    skill_id: int,
    status: str,
    error_message: Optional[str] = None,
    duration_ms: int = 0,
) -> int:
    """Create a skill call log entry.

    Args:
        conn: Database connection
        user_id: User ID
        skill_id: Skill ID
        status: Call status ('success', 'failure', 'denied')
        error_message: Error message if failed
        duration_ms: Call duration in milliseconds

    Returns:
        Created log ID
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO skill_calls (user_id, skill_id, status, error_message, duration_ms)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, skill_id, status, error_message, duration_ms),
        )
        return cur.lastrowid
