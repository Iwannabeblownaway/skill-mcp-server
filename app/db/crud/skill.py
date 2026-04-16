"""Skill CRUD operations."""

import os
from pathlib import Path
from typing import Optional

import aiomysql


# Skills root directory (relative to project root)
SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


def get_skill_content_path(skill_path: str) -> Path:
    """Get the path to SKILL.md file for a skill.

    Args:
        skill_path: Relative path to skill folder

    Returns:
        Path to SKILL.md file
    """
    return SKILLS_DIR / skill_path / "SKILL.md"


async def create(
    conn: aiomysql.Connection,
    name: str,
    description: str,
    path: str,
    version: str = "1.0",
) -> dict:
    """Create a new skill metadata record.

    Args:
        conn: Database connection
        name: Skill name (unique)
        description: Skill description
        path: Relative path to skill folder
        version: Skill version

    Returns:
        Created skill dict
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "INSERT INTO skills (name, description, path, version) VALUES (%s, %s, %s, %s)",
            (name, description, path, version),
        )
        skill_id = cur.lastrowid

        return {
            "id": skill_id,
            "name": name,
            "description": description,
            "path": path,
            "version": version,
        }


async def update(
    conn: aiomysql.Connection,
    name: str,
    description: str | None = None,
    version: str | None = None,
) -> Optional[dict]:
    """Update an existing skill metadata.

    Args:
        conn: Database connection
        name: Skill name
        description: New description (if provided)
        version: New version (if provided)

    Returns:
        Updated skill dict or None if not found
    """
    updates = []
    params = []

    if description is not None:
        updates.append("description = %s")
        params.append(description)
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
    """Delete a skill metadata record.

    Note: This only deletes the database record, not the filesystem folder.

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
        Skill dict (without content) or None if not found
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, name, description, path, version, created_at, updated_at FROM skills WHERE name = %s",
            (name,),
        )
        return await cur.fetchone()


async def get_by_id(conn: aiomysql.Connection, skill_id: int) -> Optional[dict]:
    """Get skill by ID.

    Args:
        conn: Database connection
        skill_id: Skill ID

    Returns:
        Skill dict (without content) or None if not found
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, name, description, path, version, created_at, updated_at FROM skills WHERE id = %s",
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
        List of skill dicts (without content)
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, name, description, path, version, created_at, updated_at FROM skills ORDER BY id LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return await cur.fetchall()


async def get_by_ids(conn: aiomysql.Connection, skill_ids: list[int]) -> list[dict]:
    """Get skills by IDs.

    Args:
        conn: Database connection
        skill_ids: List of skill IDs

    Returns:
        List of skill dicts (without content)
    """
    if not skill_ids:
        return []
    async with conn.cursor(aiomysql.DictCursor) as cur:
        format_ids = ",".join(["%s"] * len(skill_ids))
        await cur.execute(
            f"SELECT id, name, description, path, version, created_at, updated_at FROM skills WHERE id IN ({format_ids}) ORDER BY id",
            tuple(skill_ids),
        )
        return await cur.fetchall()


def load_skill_content(skill_path: str) -> Optional[str]:
    """Load skill content from filesystem.

    Args:
        skill_path: Relative path to skill folder

    Returns:
        Skill content (SKILL.md) or None if not found
    """
    skill_file = get_skill_content_path(skill_path)
    if skill_file.exists():
        return skill_file.read_text(encoding="utf-8")
    return None


def skill_exists(skill_path: str) -> bool:
    """Check if skill folder exists with SKILL.md.

    Args:
        skill_path: Relative path to skill folder

    Returns:
        True if skill folder with SKILL.md exists
    """
    return get_skill_content_path(skill_path).exists()
