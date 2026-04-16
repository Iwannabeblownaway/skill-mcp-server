"""Skill CRUD operations."""

from typing import Optional

import aiomysql


async def create(
    conn: aiomysql.Connection,
    name: str,
    description: str,
    content: str,
    version: str = "1.0",
) -> dict:
    """Create a new skill.

    Args:
        conn: Database connection
        name: Skill name (unique)
        description: Skill description
        content: Skill content (markdown)
        version: Skill version

    Returns:
        Created skill dict
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "INSERT INTO skills (name, description, content, version) VALUES (%s, %s, %s, %s)",
            (name, description, content, version),
        )
        skill_id = cur.lastrowid

        return {
            "id": skill_id,
            "name": name,
            "description": description,
            "content": content,
            "version": version,
        }


async def update(
    conn: aiomysql.Connection,
    name: str,
    description: str | None = None,
    content: str | None = None,
    version: str | None = None,
) -> Optional[dict]:
    """Update an existing skill.

    Args:
        conn: Database connection
        name: Skill name
        description: New description (if provided)
        content: New content (if provided)
        version: New version (if provided)

    Returns:
        Updated skill dict or None if not found
    """
    updates = []
    params = []

    if description is not None:
        updates.append("description = %s")
        params.append(description)
    if content is not None:
        updates.append("content = %s")
        params.append(content)
    if version is not None:
        updates.append("version = %s")
        params.append(version)

    if not updates:
        return await get_by_name(conn, name)

    params.append(name)
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            f"UPDATE skills SET {', '.join(updates)} WHERE name = %s", tuple(params)
        )
        if cur.rowcount == 0:
            return None
        return await get_by_name(conn, name)


async def delete(conn: aiomysql.Connection, name: str) -> bool:
    """Delete a skill.

    Args:
        conn: Database connection
        name: Skill name

    Returns:
        True if deleted, False if not found
    """
    async with conn.cursor() as cur:
        await cur.execute("DELETE FROM skills WHERE name = %s", (name,))
        return cur.rowcount > 0


async def get_by_name(conn: aiomysql.Connection, name: str) -> Optional[dict]:
    """Get skill by name.

    Args:
        conn: Database connection
        name: Skill name

    Returns:
        Skill dict or None if not found
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, name, description, content, version, created_at, updated_at FROM skills WHERE name = %s",
            (name,),
        )
        return await cur.fetchone()


async def get_by_id(conn: aiomysql.Connection, skill_id: int) -> Optional[dict]:
    """Get skill by ID.

    Args:
        conn: Database connection
        skill_id: Skill ID

    Returns:
        Skill dict or None if not found
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, name, description, content, version, created_at, updated_at FROM skills WHERE id = %s",
            (skill_id,),
        )
        return await cur.fetchone()


async def list_all(
    conn: aiomysql.Connection, limit: int = 100, offset: int = 0
) -> list[dict]:
    """List all skills.

    Args:
        conn: Database connection
        limit: Maximum number of skills to return
        offset: Number of skills to skip

    Returns:
        List of skill dicts
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, name, description, content, version, created_at, updated_at FROM skills ORDER BY id LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return await cur.fetchall()


async def get_by_ids(conn: aiomysql.Connection, skill_ids: list[int]) -> list[dict]:
    """Get skills by IDs.

    Args:
        conn: Database connection
        skill_ids: List of skill IDs

    Returns:
        List of skill dicts
    """
    if not skill_ids:
        return []
    async with conn.cursor(aiomysql.DictCursor) as cur:
        format_ids = ",".join(["%s"] * len(skill_ids))
        await cur.execute(
            f"SELECT id, name, description, content, version, created_at, updated_at FROM skills WHERE id IN ({format_ids}) ORDER BY id",
            tuple(skill_ids),
        )
        return await cur.fetchall()
