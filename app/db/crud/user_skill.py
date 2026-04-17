"""User-Skill authorization CRUD operations."""

import aiomysql


async def grant(conn: aiomysql.Connection, user_id: int, skill_id: int) -> bool:
    """Grant a skill to a user.

    Args:
        conn: Database connection
        user_id: User ID
        skill_id: Skill ID

    Returns:
        True if granted (inserted), False if already exists
    """
    async with conn.cursor() as cur:
        try:
            await cur.execute(
                "INSERT INTO user_skills (user_id, skill_id) VALUES (%s, %s)",
                (user_id, skill_id),
            )
            return True
        except aiomysql.IntegrityError:
            # Already exists
            return False


async def revoke(conn: aiomysql.Connection, user_id: int, skill_id: int) -> bool:
    """Revoke a skill from a user.

    Args:
        conn: Database connection
        user_id: User ID
        skill_id: Skill ID

    Returns:
        True if revoked, False if not found
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "DELETE FROM user_skills WHERE user_id = %s AND skill_id = %s",
            (user_id, skill_id),
        )
        return cur.rowcount > 0


async def get_user_skills(conn: aiomysql.Connection, user_id: int) -> list[dict]:
    """Get all skills granted to a user.

    Args:
        conn: Database connection
        user_id: User ID

    Returns:
        List of skill dicts (id, name, description, path)
    """
    import json

    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            """SELECT s.id, s.name, s.description, s.path, s.version,
                      s.created_at, s.updated_at, s.dependencies
               FROM skills s
               INNER JOIN user_skills us ON s.id = us.skill_id
               WHERE us.user_id = %s
               ORDER BY s.name""",
            (user_id,),
        )
        rows = await cur.fetchall()
        for row in rows:
            if row.get("dependencies"):
                row["dependencies"] = json.loads(row["dependencies"])
        return rows


async def has_skill(conn: aiomysql.Connection, user_id: int, skill_name: str) -> bool:
    """Check if a user has a specific skill.

    Args:
        conn: Database connection
        user_id: User ID
        skill_name: Skill name

    Returns:
        True if user has the skill, False otherwise
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """SELECT 1 FROM user_skills us
               INNER JOIN skills s ON us.skill_id = s.id
               WHERE us.user_id = %s AND s.name = %s
               LIMIT 1""",
            (user_id, skill_name),
        )
        return cur.rowcount > 0
