"""Skill CRUD operations."""

import os
from pathlib import Path
from typing import Optional

import aiomysql


# Skills root directory (project root / skills)
SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "skills"


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
    """Delete a skill metadata record and filesystem folder.

    Note: Deletes both the database record AND the filesystem folder.

    Args:
        conn: Database connection
        name: Skill name

    Returns:
        True if deleted, False if not found
    """
    # Get skill path first (before deleting DB record)
    skill = await get_by_name(conn, name)
    if skill is None:
        return False

    # Delete database record
    async with conn.cursor() as cur:
        await cur.execute("DELETE FROM skills WHERE name = %s", (name,))
        if cur.rowcount == 0:
            return False

    # Delete filesystem folder
    skill_dir = SKILLS_DIR / skill["path"]
    if skill_dir.exists() and skill_dir.is_dir():
        import shutil

        shutil.rmtree(skill_dir)

    return True


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


def load_skill_folder_as_json(skill_path: str) -> Optional[dict]:
    """Load entire skill folder as JSON (file_path -> content).

    Args:
        skill_path: Relative path to skill folder

    Returns:
        Dict of {relative_file_path: file_content} or None if folder not found
    """
    import json

    skill_dir = SKILLS_DIR / skill_path
    if not skill_dir.exists() or not skill_dir.is_dir():
        return None

    result = {}
    for file_path in skill_dir.rglob("*"):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(skill_dir))
            try:
                content = file_path.read_text(encoding="utf-8")
                result[rel_path] = content
            except Exception:
                # Binary files or read errors - skip
                result[rel_path] = None

    return result if result else None


async def update_content_json(
    conn: aiomysql.Connection, name: str, content_json: dict
) -> bool:
    """Update skill content_json in database.

    Args:
        conn: Database connection
        name: Skill name
        content_json: Dict of {file_path: content}

    Returns:
        True if updated, False if skill not found
    """
    import json

    async with conn.cursor() as cur:
        await cur.execute(
            "UPDATE skills SET content_json = %s WHERE name = %s",
            (json.dumps(content_json, ensure_ascii=False), name),
        )
        return cur.rowcount > 0


async def get_content_json(conn: aiomysql.Connection, name: str) -> Optional[dict]:
    """Get skill content_json from database.

    Args:
        conn: Database connection
        name: Skill name

    Returns:
        Dict of {file_path: content} or None if not found
    """
    import json

    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT content_json FROM skills WHERE name = %s",
            (name,),
        )
        row = await cur.fetchone()
        if row and row.get("content_json"):
            return json.loads(row["content_json"])
        return None


def load_skill_index(skill_path: str) -> Optional[dict[str, int]]:
    """Load skill folder file index (path -> size, no content).

    Args:
        skill_path: Relative path to skill folder

    Returns:
        Dict of {relative_file_path: file_size_in_bytes} or None if folder not found
    """
    skill_dir = SKILLS_DIR / skill_path
    if not skill_dir.exists() or not skill_dir.is_dir():
        return None

    result = {}
    for file_path in skill_dir.rglob("*"):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(skill_dir))
            try:
                result[rel_path] = file_path.stat().st_size
            except Exception:
                result[rel_path] = 0

    return result if result else None


def load_single_file(skill_path: str, file_path: str) -> Optional[str]:
    """Load a single file from skill folder.

    Args:
        skill_path: Relative path to skill folder
        file_path: Relative path within skill folder (e.g., "SKILL.md" or "references/template.md")

    Returns:
        File content as string or None if file not found
    """
    skill_file = SKILLS_DIR / skill_path / file_path
    if not skill_file.exists() or not skill_file.is_file():
        return None

    try:
        return skill_file.read_text(encoding="utf-8")
    except Exception:
        return None
