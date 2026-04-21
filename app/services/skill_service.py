"""Skill service - business logic for skill operations."""

import json
from typing import Any, Optional, Union
from urllib.parse import urlparse

from app.db.session import get_db
from app.db.crud import skill as skill_crud
from app.db.crud import user_skill as user_skill_crud
from app.db.crud import call_log as call_log_crud


def extract_urls_from_mcp_config(mcp_config: dict) -> list[str]:
    """Extract base URLs from MCP config, removing all query parameters.

    Handles flexible formats:
    - Simple URL strings: {"server-name": "https://..."}
    - Object with url field: {"server-name": {"url": "https://..."}}
    - Nested mcpServers wrapper: {"mcpServers": {"server": {...}}}
    - Arrays of servers: [{"url": "https://..."}]
    - Various url field names: url, remote_url, endpoint, server_url, uri

    Args:
        mcp_config: MCP configuration dict

    Returns:
        List of base URLs with all query params stripped.
    """
    # Known URL field names in various MCP implementations
    URL_FIELD_NAMES = ("url", "baseUrl", "remote_url", "endpoint", "server_url", "uri")

    def _extract_from_value(value: Any) -> None:
        """Extract URL from a single config value (recursive helper)."""
        if isinstance(value, str):
            # Simple URL string
            _add_url(value)
        elif isinstance(value, dict):
            # Check if this dict has a URL field directly
            url = None
            for field in URL_FIELD_NAMES:
                if field in value:
                    url = value[field]
                    break

            if url and isinstance(url, str):
                _add_url(url)
            elif not url:
                # Local server (has command/args but no url) - skip
                if "command" not in value and "url" not in value:
                    # Could be a nested config, try to find URL fields recursively
                    for v in value.values():
                        _extract_from_value(v)
        elif isinstance(value, list):
            # Array of server configs
            for item in value:
                _extract_from_value(item)

    def _add_url(url: str) -> None:
        """Parse and add URL if valid, skipping query parameters."""
        if not url or not isinstance(url, str):
            return
        url = url.strip()
        if not url:
            return
        # Strip trailing slashes for consistency
        url = url.rstrip("/")
        # Only process if looks like a URL
        if not url.startswith(("http://", "https://", "//")):
            return
        # Handle //domain.com style (protocol-relative URL)
        if url.startswith("//"):
            url = "https:" + url
        try:
            parsed = urlparse(url)
            if parsed.netloc:
                base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if base_url not in urls:
                    urls.append(base_url)
        except (ValueError, AttributeError):
            pass

    urls: list[str] = []

    # Handle nested mcpServers wrapper
    if "mcpServers" in mcp_config:
        mcp_config = mcp_config["mcpServers"]

    # Iterate over config items
    for key, value in mcp_config.items():
        if key in ("mcpServers", "servers"):
            # Nested servers object
            if isinstance(value, dict):
                for v in value.values():
                    _extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    _extract_from_value(item)
        else:
            _extract_from_value(value)

    return urls


async def get_user_skills(user_id: int) -> list[dict]:
    """Get all skills authorized for a user.

    Args:
        user_id: User ID

    Returns:
        List of skill dicts with name, description, and dependencies
    """
    async with get_db() as conn:
        skills = await user_skill_crud.get_user_skills(conn, user_id)
        result = []
        for s in skills:
            skill_data = {
                "name": s["name"],
                "description": s.get("description", ""),
                "dependencies": s.get("dependencies", []),
            }
            result.append(skill_data)
        return result


async def check_permission(user_id: int, skill_name: str, is_admin: bool = False) -> bool:
    """Check if a user has permission to access a skill.

    Args:
        user_id: User ID
        skill_name: Skill name
        is_admin: If True, skip permission check (admin has all permissions)

    Returns:
        True if user has permission, False otherwise
    """
    if is_admin:
        return True
    async with get_db() as conn:
        return await user_skill_crud.has_skill(conn, user_id, skill_name)


async def get_skill_content(
    user_id: int, skill_name: str, is_admin: bool = False
) -> tuple[Optional[str], Optional[str]]:
    """Get the SKILL.md content of a skill if user has permission.

    Args:
        user_id: User ID
        skill_name: Skill name
        is_admin: If True, skip permission check (admin has all permissions)

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

        # Check permission (skip for admin)
        if not is_admin:
            has_perm = await user_skill_crud.has_skill(conn, user_id, skill_name)
            if not has_perm:
                return None, "Permission denied"

        # Load from filesystem
        content = skill_crud.load_skill_content(sk["path"])
        if content is None:
            return None, "Skill file not found"

        return content, None


async def get_skill_content_json(
    user_id: int, skill_name: str, is_admin: bool = False
) -> tuple[Optional[dict], Optional[str]]:
    """Get the entire skill folder as JSON if user has permission.

    Args:
        user_id: User ID
        skill_name: Skill name
        is_admin: If True, skip permission check (admin has all permissions)

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

        # Check permission (skip for admin)
        if not is_admin:
            has_perm = await user_skill_crud.has_skill(conn, user_id, skill_name)
            if not has_perm:
                return None, "Permission denied"

        # Load from filesystem
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
    user_id: int, skill_name: str, is_admin: bool = False
) -> tuple[Optional[dict], Optional[str]]:
    """Get skill file index (file paths + sizes, no content).

    Args:
        user_id: User ID
        skill_name: Skill name
        is_admin: If True, skip permission check (admin has all permissions)

    Returns:
        Tuple of ({name, version, files, _mcp_skill_context}, error). If successful, error is None.
    """
    async with get_db() as conn:
        # Check if skill exists
        sk = await skill_crud.get_by_name(conn, skill_name)
        if sk is None:
            return None, "Skill not found"

        # Check permission (skip for admin)
        if not is_admin:
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
    user_id: int, skill_name: str, file_path: str, is_admin: bool = False
) -> tuple[Optional[str], Optional[str]]:
    """Get content of a single file from skill folder.

    Args:
        user_id: User ID
        skill_name: Skill name
        file_path: Relative path within skill folder
        is_admin: If True, skip permission check (admin has all permissions)

    Returns:
        Tuple of (file_content_with_context, error). If successful, error is None.
        The content includes _mcp_skill_context with all_files list and hint.
    """
    async with get_db() as conn:
        # Check if skill exists
        sk = await skill_crud.get_by_name(conn, skill_name)
        if sk is None:
            return None, "Skill not found"

        # Check permission (skip for admin)
        if not is_admin:
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
