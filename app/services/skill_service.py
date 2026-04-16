"""Skill service - business logic for skill operations."""

from typing import Optional

from app.db.session import get_db
from app.db.crud import skill as skill_crud
from app.db.crud import user_skill as user_skill_crud
from app.db.crud import call_log as call_log_crud


async def get_user_skills(user_id: int) -> list[dict]:
    """Get all skills authorized for a user.

    Args:
        user_id: User ID

    Returns:
        List of skill dicts with name and description
    """
    async with get_db() as conn:
        skills = await user_skill_crud.get_user_skills(conn, user_id)
        return [{"name": s["name"], "description": s["description"]} for s in skills]


async def check_permission(user_id: int, skill_name: str) -> bool:
    """Check if a user has permission to access a skill.

    Args:
        user_id: User ID
        skill_name: Skill name

    Returns:
        True if user has permission, False otherwise
    """
    async with get_db() as conn:
        return await user_skill_crud.has_skill(conn, user_id, skill_name)


async def get_skill_content(
    user_id: int, skill_name: str
) -> tuple[Optional[str], Optional[str]]:
    """Get the content of a skill if user has permission.

    Args:
        user_id: User ID
        skill_name: Skill name

    Returns:
        Tuple of (content, error). If successful, error is None.
        If skill not found, error = "Skill not found".
        If no permission, error = "Permission denied".
        If file not found, error = "Skill file not found".
    """
    async with get_db() as conn:
        # Check if skill exists
        sk = await skill_crud.get_by_name(conn, skill_name)
        if sk is None:
            return None, "Skill not found"

        # Check permission
        has_perm = await user_skill_crud.has_skill(conn, user_id, skill_name)
        if not has_perm:
            return None, "Permission denied"

        # Load content from filesystem
        content = skill_crud.load_skill_content(sk["path"])
        if content is None:
            return None, "Skill file not found"

        return content, None


async def log_call(
    user_id: int, skill_name: str, status: str, error_msg: str, duration_ms: int
) -> None:
    """Log a skill call.

    Args:
        user_id: User ID
        skill_name: Skill name
        status: Call status ('success', 'failure', 'denied')
        error_msg: Error message if failed
        duration_ms: Call duration in milliseconds
    """
    async with get_db() as conn:
        # Get skill_id
        sk = await skill_crud.get_by_name(conn, skill_name)
        if sk is None:
            return

        await call_log_crud.create_log(
            conn,
            user_id=user_id,
            skill_id=sk["id"],
            status=status,
            error_message=error_msg if error_msg else None,
            duration_ms=duration_ms,
        )
