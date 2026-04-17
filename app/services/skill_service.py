"""Skill service - business logic for skill operations."""

import json
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
    """Get the SKILL.md content of a skill if user has permission.

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

        # Try DB content_json first, fall back to filesystem
        content_json = await skill_crud.get_content_json(conn, skill_name)
        if content_json and "SKILL.md" in content_json:
            return content_json["SKILL.md"], None

        # Fall back to filesystem
        content = skill_crud.load_skill_content(sk["path"])
        if content is None:
            return None, "Skill file not found"

        return content, None


async def get_skill_content_json(
    user_id: int, skill_name: str
) -> tuple[Optional[dict], Optional[str]]:
    """Get the entire skill folder as JSON if user has permission.

    Args:
        user_id: User ID
        skill_name: Skill name

    Returns:
        Tuple of ({file_path: content}, error). If successful, error is None.
        If skill not found, error = "Skill not found".
        If no permission, error = "Permission denied".
        If folder not found, error = "Skill folder not found".
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

        # Try DB content_json first
        content_json = await skill_crud.get_content_json(conn, skill_name)
        if content_json:
            return content_json, None

        # Fall back to filesystem
        content_json = skill_crud.load_skill_folder_as_json(sk["path"])
        if content_json is None:
            return None, "Skill folder not found"

        return content_json, None


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


async def get_skill_index(
    user_id: int, skill_name: str
) -> tuple[Optional[dict], Optional[str]]:
    """Get skill file index (file paths + sizes, no content).

    Args:
        user_id: User ID
        skill_name: Skill name

    Returns:
        Tuple of ({name, version, files, _mcp_skill_context}, error). If successful, error is None.
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

        # Get index from filesystem
        index = skill_crud.load_skill_index(sk["path"])
        if index is None:
            return None, "Skill folder not found"

        all_files = list(index.keys())
        return {
            "name": skill_name,
            "version": sk.get("version", "1.0"),
            "files": index,
            "_mcp_skill_context": {
                "skill_name": skill_name,
                "all_files": all_files,
                "hint": "此 skill 包含多个文件。如需获取某个文件的内容，请调用 get_skill_file 并指定 file_path。如需查看完整文件列表及用途，请查阅 SKILL.md。",
            },
        }, None


async def get_skill_file(
    user_id: int, skill_name: str, file_path: str
) -> tuple[Optional[str], Optional[str]]:
    """Get content of a single file from skill folder.

    Args:
        user_id: User ID
        skill_name: Skill name
        file_path: Relative path within skill folder

    Returns:
        Tuple of (file_content_with_context, error). If successful, error is None.
        The content includes _mcp_skill_context with all_files list and hint.
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

        # Get all files index for context
        index = skill_crud.load_skill_index(sk["path"])
        if index is None:
            return None, "Skill folder not found"
        all_files = list(index.keys())

        # Load single file
        content = skill_crud.load_single_file(sk["path"], file_path)
        if content is None:
            return None, f"File '{file_path}' not found"

        # Append _mcp_skill_context as HTML comment at the end
        other_files = [f for f in all_files if f != file_path]
        context_data = {
            "skill_name": skill_name,
            "requested_file": file_path,
            "all_files": all_files,
            "hint": f"你正在读取 {file_path}，此 skill 还包含其他文件：{', '.join(other_files)} 等。如需读取其他文件，请调用 get_skill_file 并指定 file_path。",
        }
        context_json = f"\n\n<!-- _mcp_skill_context\n{json.dumps(context_data, ensure_ascii=False, indent=2)}\n-->"
        return content + context_json, None
