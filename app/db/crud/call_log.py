"""Skill call log CRUD operations."""

from datetime import datetime
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


async def list_logs(
    conn: aiomysql.Connection,
    user_id: Optional[int] = None,
    skill_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List skill call logs with optional filters.

    Args:
        conn: Database connection
        user_id: Filter by user ID (optional)
        skill_name: Filter by skill name (optional)
        start_time: Filter by start time (optional)
        end_time: Filter by end time (optional)
        limit: Maximum number of logs to return
        offset: Number of logs to skip

    Returns:
        Tuple of (logs list, total count)
    """
    # Build WHERE clause dynamically
    conditions = []
    params = []

    if user_id is not None:
        conditions.append("sc.user_id = %s")
        params.append(user_id)

    if skill_name is not None:
        conditions.append("s.name = %s")
        params.append(skill_name)

    if start_time is not None:
        conditions.append("sc.call_time >= %s")
        params.append(start_time)

    if end_time is not None:
        conditions.append("sc.call_time <= %s")
        params.append(end_time)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get total count
    async with conn.cursor() as cur:
        count_sql = f"""
            SELECT COUNT(*) as total
            FROM skill_calls sc
            LEFT JOIN skills s ON sc.skill_id = s.id
            WHERE {where_clause}
        """
        await cur.execute(count_sql, tuple(params))
        total = (await cur.fetchone())[0]

    # Get paginated results with skill name
    async with conn.cursor(aiomysql.DictCursor) as cur:
        sql = f"""
            SELECT sc.id, sc.user_id, sc.skill_id, s.name as skill_name,
                   sc.call_time, sc.status, sc.error_message, sc.duration_ms,
                   u.username
            FROM skill_calls sc
            LEFT JOIN skills s ON sc.skill_id = s.id
            LEFT JOIN users u ON sc.user_id = u.id
            WHERE {where_clause}
            ORDER BY sc.call_time DESC
            LIMIT %s OFFSET %s
        """
        await cur.execute(sql, tuple(params + [limit, offset]))
        logs = await cur.fetchall()

    return logs, total
