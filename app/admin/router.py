"""Admin panel routes."""

import json
import os
import secrets
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Form, HTTPException, Query, UploadFile, File, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.datastructures import URL

from app.db.session import get_db
from app.db.crud import user as user_crud
from app.db.crud import skill as skill_crud
from app.db.crud import user_skill as user_skill_crud
from app.db.crud import call_log as call_log_crud
from app.utils.redis_client import redis_client

from app.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])

# Session configuration
ADMIN_SESSION_TTL = settings.ADMIN_SESSION_TTL
SESSION_COOKIE_NAME = "admin_session"
SESSION_KEY_PREFIX = "admin:session:"


def render_template(template_name: str, context: dict) -> HTMLResponse:
    """Render a template and return HTMLResponse."""
    env = get_templates()
    template = env.get_template(template_name)
    html = template.render(context)
    return HTMLResponse(html)


def get_templates():
    """Create a fresh Jinja2 environment with cache disabled.

    This avoids issues with uvicorn hot-reload preserving stale cache state.
    """
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path

    # Use absolute path based on this file's location to avoid working directory issues
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(template_dir),
        auto_reload=True,
        cache_size=0  # Disable cache
    )

    return env


def redirect_with_message(url: str, message: str, message_type: str = "success") -> HTMLResponse:
    """Create a redirect response with flash message via sessionStorage.

    The target page will read from sessionStorage and display the message.
    Uses hex escaping (\\x3c, \\x3e) for < > to prevent XSS in script context.
    """
    import json
    import re

    # JSON encode first, then apply JS hex escaping for < and >
    def js_hex_escape(s):
        """Escape string for JavaScript context using hex escapes."""
        # json.dumps already escapes " and \
        json_str = json.dumps(s)
        # Replace < and > with hex escapes to prevent breaking HTML script block
        # \x3c = <, \x3e = > in JS strings
        json_str = json_str.replace("<", "\\x3c").replace(">", "\\x3e")
        return json_str

    safe_url = js_hex_escape(url)
    safe_type = js_hex_escape(message_type)
    safe_msg = js_hex_escape(message)

    script = f"""<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url={safe_url[1:-1]}"></head><body><script>
sessionStorage.setItem('flash_message', {safe_msg});
sessionStorage.setItem('flash_message_type', {safe_type});
window.location.href = {safe_url};
</script></body></html>"""
    return HTMLResponse(content=script)


def get_message(request: Request) -> Optional[dict]:
    """Get flash message - not used anymore, kept for template compatibility."""
    return None


def set_message(request: Request, text: str, type: str = "success"):
    """Set flash message (deprecated - use redirect_with_message instead)."""
    request.state.message = {"text": text, "type": type}


# ==================== Helper Functions ====================

def _flatten_single_top_level_dir(entries: list[str]) -> str:
    """Detect WinRAR-style nested duplicate directories that need stripping.

    Only strips when ALL entries have consecutive duplicate directory names
    at the start of their paths (e.g., "a/a/SKILL.md"). This handles the
    WinRAR case where compressing a folder from inside creates nested duplicate
    parent directories.

    Normal cases are NOT stripped:
    - "skill/SKILL.md" -> returns "" (no stripping)
    - "a/b/SKILL.md" -> returns "" (no consecutive duplicates)

    WinRAR case IS stripped:
    - "skill/skill/SKILL.md" -> returns "skill" (strip one level)

    Args:
        entries: List of file entry paths

    Returns:
        Single directory name to strip if consecutive duplicates detected,
        empty string otherwise.
    """
    if not entries:
        return ""

    # Normalize all separators to forward slashes
    normalized = [e.replace("\\", "/") for e in entries]
    parts_list = [list(filter(None, e.split("/"))) for e in normalized]
    if not all(parts_list) or len(parts_list[0]) < 2:
        return ""

    # Check if we have consecutive duplicate directory names at the start
    first_parts = parts_list[0]
    if len(first_parts) < 2:
        return ""

    # Count consecutive occurrences of first directory name
    first_name = first_parts[0]
    consecutive_count = 1
    for i in range(1, len(first_parts)):
        if first_parts[i] == first_name:
            consecutive_count += 1
        else:
            break

    # Only strip if we have 2+ consecutive duplicates AND all entries share this
    if consecutive_count < 2:
        return ""

    # Verify ALL entries have at least this many consecutive duplicates
    for parts in parts_list:
        if len(parts) < consecutive_count:
            return ""
        for i in range(consecutive_count):
            if parts[i] != first_name:
                return ""

    # Return just ONE occurrence to strip (keeps one level)
    return first_name


def _parse_dependencies(dependencies_input: str) -> list:
    """Parse dependencies from various input formats.

    Supports:
    - Comma-separated: "dep1,dep2,dep3"
    - JSON array: '["dep1", "dep2"]'
    - MCP config JSON: '{"mcpServers": {"sorftime": {}, "aws": {}}}'

    Args:
        dependencies_input: Raw dependencies string from form input.

    Returns:
        List of dependency names (server keys from mcpServers).
    """
    if not dependencies_input or not dependencies_input.strip():
        return []

    # Try JSON array format first
    try:
        parsed = json.loads(dependencies_input)
        if isinstance(parsed, list):
            return [d.strip() for d in parsed if d.strip()]
        elif isinstance(parsed, dict) and "mcpServers" in parsed:
            # Full MCP config format - extract server names
            return list(parsed.get("mcpServers", {}).keys())
    except json.JSONDecodeError:
        pass

    # Fall back to comma-separated
    return [d.strip() for d in dependencies_input.split(",") if d.strip()]


def _build_skill_package(skill_name: str, skill_path: str) -> Path:
    """Build a .skill package (zip file) from skill folder.

    Args:
        skill_name: Skill name
        skill_path: Relative path to skill folder

    Returns:
        Path to the generated .skill package (actually a zip file)
    """
    from pathlib import PurePosixPath

    skill_dir = skill_crud.SKILLS_DIR / skill_path
    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill folder not found: {skill_dir}")

    # Create packages directory alongside skills
    packages_dir = skill_crud.SKILLS_DIR.parent / "skill_packages"
    packages_dir.mkdir(exist_ok=True)

    # Build .skill file path (still a zip internally)
    package_path = packages_dir / f"{skill_name}.skill"

    # Create zip - use forward slashes for cross-platform compatibility
    with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in skill_dir.rglob("*"):
            if file_path.is_file():
                # Use PurePosixPath to ensure forward slashes in zip
                arcname = PurePosixPath(file_path.relative_to(skill_dir))
                zf.write(file_path, str(arcname))

    return package_path


def _get_skill_package_path(skill_name: str) -> Optional[Path]:
    """Get path to .skill package if it exists.

    Args:
        skill_name: Skill name

    Returns:
        Path to .skill package or None if not found
    """
    packages_dir = skill_crud.SKILLS_DIR.parent / "skill_packages"
    package_path = packages_dir / f"{skill_name}.skill"
    return package_path if package_path.exists() else None


# ==================== Session Management ====================

async def create_admin_session(user: dict) -> str:
    """Create an admin session and return session ID."""
    session_id = secrets.token_urlsafe(32)
    session_data = {
        "id": user["id"],  # Use internal id (int) for DB queries
        "username": user["username"],
        "role": user["role"],
    }
    await redis_client.put_session(
        f"{SESSION_KEY_PREFIX}{session_id}",
        session_data,
        ttl=ADMIN_SESSION_TTL,
    )
    return session_id


async def get_admin_session(session_id: str) -> Optional[dict]:
    """Get admin session data."""
    if not session_id:
        return None
    return await redis_client.get_session(f"{SESSION_KEY_PREFIX}{session_id}")


async def delete_admin_session(session_id: str) -> None:
    """Delete an admin session."""
    if session_id:
        await redis_client.delete_session(f"{SESSION_KEY_PREFIX}{session_id}")


def get_session_id(request: Request) -> Optional[str]:
    """Extract session ID from cookie."""
    return request.cookies.get(SESSION_COOKIE_NAME)


async def get_current_admin_user(request: Request) -> Optional[dict]:
    """Get current logged-in admin user from session."""
    session_id = get_session_id(request)
    if not session_id:
        return None
    session_data = await get_admin_session(session_id)
    if not session_data:
        return None
    # Fetch fresh user data from database
    async with get_db() as conn:
        user = await user_crud.get_by_id(conn, session_data["id"])
    return user


async def require_admin(request: Request) -> dict:
    """Dependency that requires admin authentication.

    Raises HTTPException if not authenticated.
    """
    user = await get_current_admin_user(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    if user.get("role") != "admin":
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    return user


# ==================== Login/Logout Routes ====================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page - redirect if already logged in."""
    session_id = get_session_id(request)
    if session_id:
        session_data = await get_admin_session(session_id)
        if session_data:
            return RedirectResponse(url="/admin", status_code=303)

    return render_template("login.html", {
        "request": request,
        "error": None,
    })


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, api_key: str = Form(...)):
    """Process login request using API key."""
    async with get_db() as conn:
        # Find user by API key and verify they are admin
        user = await user_crud.get_by_api_key(conn, api_key.strip())

    if not user:
        return render_template("login.html", {
            "request": request,
            "error": "无效的 API Key",
        })

    if user.get("role") != "admin":
        return render_template("login.html", {
            "request": request,
            "error": "只有管理员账户可以登录后台",
        })

    # Create session
    session_id = await create_admin_session(user)

    # Create response with redirect to admin dashboard
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=ADMIN_SESSION_TTL,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """Logout - delete session and redirect to login."""
    session_id = get_session_id(request)
    if session_id:
        await delete_admin_session(session_id)

    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


# ==================== Dashboard ====================

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, admin_user: dict = Depends(require_admin)):
    """Dashboard overview."""
    async with get_db() as conn:
        # User stats
        users = await user_crud.list_users(conn, limit=1000)
        user_count = len(users)

        # Skill stats
        skills = await skill_crud.list_all(conn, limit=1000)
        skill_count = len(skills)

        # Auth stats
        auth_count = 0
        for sk in skills:
            grants = await user_skill_crud.get_user_skills(conn, sk["id"])
            auth_count += len(grants)

    return render_template("dashboard.html", {
        "request": request,
        "message": get_message(request),
        "user_count": user_count,
        "skill_count": skill_count,
        "auth_count": auth_count,
        "admin_user": admin_user,
    })


# ==================== Users ====================

@router.get("/users", response_class=HTMLResponse)
async def user_list(request: Request, admin_user: dict = Depends(require_admin)):
    """List all users."""
    async with get_db() as conn:
        users = await user_crud.list_users(conn, limit=1000)

    return render_template("users/list.html", {
        "request": request,
        "message": get_message(request),
        "users": users,
        "admin_user": admin_user,
    })


@router.get("/users/create", response_class=HTMLResponse)
async def user_create_form(request: Request, admin_user: dict = Depends(require_admin)):
    """User creation form."""
    return render_template("users/create.html", {
        "request": request,
        "message": get_message(request),
        "admin_user": admin_user,
    })


@router.post("/users/create", response_class=HTMLResponse)
async def user_create(
    request: Request,
    admin_user: dict = Depends(require_admin),
    user_id: str = Form(""),
    username: str = Form(...),
    role: str = Form("user"),
):
    """Create a new user."""
    import secrets

    # Generate user_id if not provided
    if user_id.strip() == "":
        user_id_value = None
    else:
        user_id_value = user_id.strip()

    async with get_db() as conn:
        # Check if user_id already exists (only if provided)
        if user_id_value:
            existing = await user_crud.get_by_user_id(conn, user_id_value)
            if existing:
                return redirect_with_message(
                    "/admin/users/create",
                    f"用户 ID '{user_id}' 已存在",
                    "error"
                )
        else:
            # Generate a unique user_id if not provided
            attempts = 0
            while attempts < 5:
                generated_id = secrets.token_hex(8)
                existing = await user_crud.get_by_user_id(conn, generated_id)
                if not existing:
                    user_id_value = generated_id
                    break
                attempts += 1
            if not user_id_value:
                return redirect_with_message(
                    "/admin/users/create",
                    "用户 ID 生成失败，请重试",
                    "error"
                )

        user = await user_crud.create(conn, user_id=user_id_value, username=username, role=role)

    return redirect_with_message(
        "/admin/users",
        f"用户创建成功！API Key: {user['api_key']}（请妥善保存）",
        "success"
    )


@router.post("/users/{id}/reset-key", response_class=HTMLResponse)
async def user_reset_key(request: Request, id: int, admin_user: dict = Depends(require_admin)):
    """Reset user's API key."""
    async with get_db() as conn:
        user = await user_crud.get_by_id(conn, id)
        if not user:
            return redirect_with_message("/admin/users", "用户不存在", "error")

        # Reset API key to new random value
        new_user = await user_crud.reset_api_key(conn, id)
        if not new_user:
            return redirect_with_message("/admin/users", "重置失败", "error")

    return redirect_with_message(
        f"/admin/users/{id}",
        f"API Key 已重置！新 Key: {new_user['api_key']}（请妥善保存）",
        "success"
    )


@router.post("/users/{id}/update", response_class=HTMLResponse)
async def user_update(
    request: Request,
    id: int,
    admin_user: dict = Depends(require_admin),
    username: str = Form(""),
    user_id_value: str = Form(""),
    role: str = Form(""),
):
    """Update user info (username, user_id, role)."""
    async with get_db() as conn:
        user = await user_crud.get_by_id(conn, id)
        if not user:
            return redirect_with_message("/admin/users", "用户不存在", "error")

        # Check if new user_id conflicts with existing users
        new_user_id_val = user_id_value if user_id_value.strip() != "" else None
        if new_user_id_val and new_user_id_val != user["user_id"]:
            existing = await user_crud.get_by_user_id(conn, new_user_id_val)
            if existing and existing["id"] != id:
                return redirect_with_message(
                    f"/admin/users/{id}",
                    f"用户 ID '{user_id_value}' 已被使用",
                    "error"
                )

        # Validate role
        new_role = role if role in ("admin", "user") else user["role"]

        # Update user
        await user_crud.update(
            conn,
            id,
            username=username if username.strip() != "" else None,
            user_id_value=new_user_id_val,
            role=new_role,
        )

    return redirect_with_message(
        f"/admin/users/{id}",
        "用户信息已更新",
        "success"
    )


@router.get("/users/{id}", response_class=HTMLResponse)
async def user_detail(request: Request, id: int, admin_user: dict = Depends(require_admin)):
    """User detail with skills."""
    async with get_db() as conn:
        user = await user_crud.get_by_id(conn, id)
        if not user:
            return redirect_with_message("/admin/users", "用户不存在", "error")

        all_skills = await skill_crud.list_all(conn, limit=1000)
        # Only active skills can be granted
        active_skills = [sk for sk in all_skills if sk.get("status") == "active"]

        # Admin users have all skills implicitly
        if user["role"] == "admin":
            user_skills = active_skills
            available_skills = []
        else:
            user_skills = await user_skill_crud.get_user_skills(conn, id)
            # Filter out draft skills from user's skill list
            user_skills = [sk for sk in user_skills if sk.get("status") == "active"]
            user_skill_ids = {sk["id"] for sk in user_skills}
            available_skills = [sk for sk in active_skills if sk["id"] not in user_skill_ids]

    return render_template("users/detail.html", {
        "request": request,
        "message": get_message(request),
        "user": user,
        "user_skills": user_skills,
        "available_skills": available_skills,
        "admin_user": admin_user,
    })


@router.post("/users/{id}/grant", response_class=HTMLResponse)
async def user_grant_skill(
    request: Request,
    id: int,
    admin_user: dict = Depends(require_admin),
    skill_id: int = Form(...),
):
    """Grant a skill to user (only active skills)."""
    async with get_db() as conn:
        user = await user_crud.get_by_id(conn, id)
        if not user:
            return redirect_with_message("/admin/users", "用户不存在", "error")

        skill = await skill_crud.get_by_id(conn, skill_id)
        if not skill:
            return redirect_with_message(f"/admin/users/{id}", "技能不存在", "error")
        if skill.get("status") != "active":
            return redirect_with_message(f"/admin/users/{id}", f"技能 '{skill['name']}' 尚未激活，无法授权", "error")

        await user_skill_crud.grant(conn, id, skill_id)

    return redirect_with_message(f"/admin/users/{id}", "技能授权成功", "success")


@router.post("/users/{id}/revoke/{skill_id}", response_class=HTMLResponse)
async def user_revoke_skill(request: Request, id: int, skill_id: int, admin_user: dict = Depends(require_admin)):
    """Revoke a skill from user."""
    async with get_db() as conn:
        await user_skill_crud.revoke(conn, id, skill_id)

    return redirect_with_message(f"/admin/users/{id}", "技能已撤销", "success")


@router.post("/users/{id}/delete", response_class=HTMLResponse)
async def user_delete(request: Request, id: int, admin_user: dict = Depends(require_admin)):
    """Delete a user."""
    async with get_db() as conn:
        user = await user_crud.get_by_id(conn, id)
        if not user:
            return redirect_with_message("/admin/users", "用户不存在", "error")

        # Delete user (cascade will handle user_skills)
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM users WHERE id = %s", (id,))
        await conn.commit()

    return redirect_with_message("/admin/users", f"用户 {user['username']} 已删除", "success")


# ==================== Skills ====================

@router.get("/skills", response_class=HTMLResponse)
async def skill_list(request: Request, admin_user: dict = Depends(require_admin)):
    """List all skills."""
    async with get_db() as conn:
        skills = await skill_crud.list_all(conn, limit=1000)

    return render_template("skills/list.html", {
        "request": request,
        "message": get_message(request),
        "skills": skills,
        "admin_user": admin_user,
    })


@router.get("/skills/create", response_class=HTMLResponse)
async def skill_create_form(request: Request, admin_user: dict = Depends(require_admin)):
    """Skill creation form."""
    return render_template("skills/create.html", {
        "request": request,
        "message": get_message(request),
        "admin_user": admin_user,
    })


@router.post("/skills/create", response_class=HTMLResponse)
async def skill_create(
    request: Request,
    admin_user: dict = Depends(require_admin),
    name: str = Form(...),
    description: str = Form(""),
    dependencies: str = Form(""),
):
    """Create a new skill (metadata only)."""
    deps = _parse_dependencies(dependencies)

    async with get_db() as conn:
        existing = await skill_crud.get_by_name(conn, name)
        if existing:
            return redirect_with_message(
                "/admin/skills/create",
                f"技能 '{name}' 已存在",
                "error"
            )

        skill = await skill_crud.create(
            conn,
            name=name,
            description=description,
            path=name,
            dependencies=deps,
            status="draft",
        )

    return redirect_with_message(
        f"/admin/skills/{skill['id']}",
        f"技能 '{name}' 创建成功，请上传文件",
        "success"
    )


@router.get("/skills/{skill_id}", response_class=HTMLResponse)
async def skill_detail(request: Request, skill_id: int, admin_user: dict = Depends(require_admin)):
    """Skill detail with files."""
    async with get_db() as conn:
        skill = await skill_crud.get_by_id(conn, skill_id)
        if not skill:
            return redirect_with_message("/admin/skills", "技能不存在", "error")

        # Get files
        skill_index = skill_crud.load_skill_index(skill["path"])
        files = list(skill_index.keys()) if skill_index else []

        # Get users who have this skill
        all_users = await user_crud.list_users(conn, limit=1000)
        users_with_skill = []
        for user in all_users:
            has = await user_skill_crud.has_skill(conn, user["id"], skill["name"])
            if has:
                users_with_skill.append(user)

    return render_template("skills/detail.html", {
        "request": request,
        "message": get_message(request),
        "skill": skill,
        "files": files,
        "users_with_skill": users_with_skill,
        "admin_user": admin_user,
    })


@router.post("/skills/{skill_id}/upload", response_class=HTMLResponse)
async def skill_upload(
    request: Request,
    skill_id: int,
    admin_user: dict = Depends(require_admin),
    file: UploadFile = File(...),
):
    """Upload a file to skill."""
    from pathlib import Path
    import zipfile
    import io

    filename = file.filename or ""
    file_content = await file.read()

    async with get_db() as conn:
        skill = await skill_crud.get_by_id(conn, skill_id)
        if not skill:
            return redirect_with_message("/admin/skills", "技能不存在", "error")

        # Use full path: SKILLS_DIR / skill_path
        skill_dir = skill_crud.SKILLS_DIR / skill["path"]

        # Handle archive upload - clear folder first, then extract
        # Supported: .zip, .skill (zip format), .tar, .tar.gz, .tgz, .tar.bz2, .tar.xz
        archive_extensions = (".zip", ".skill", ".tar", ".gz", ".bz2", ".xz")
        is_archive = filename.endswith(archive_extensions) and (
            zipfile.is_zipfile(io.BytesIO(file_content)) or
            filename.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz"))
        )

        if is_archive:
            # Clear existing files
            if skill_dir.exists():
                import shutil
                shutil.rmtree(skill_dir)
            skill_dir.mkdir(parents=True, exist_ok=True)

            # Extract based on archive type
            file_io = io.BytesIO(file_content)
            if zipfile.is_zipfile(file_io):
                # .zip or .skill - first collect all entries to detect common prefix
                with zipfile.ZipFile(file_io, "r") as zf:
                    entries = [info.filename.replace("\\", "/") for info in zf.infolist() if not info.is_dir()]
                    common_prefix = _flatten_single_top_level_dir(entries)

                    # Also check if first directory matches skill name (common case)
                    # If zip contains "skill-auditor/SKILL.md" and skill_dir is already
                    # "skills/skill-auditor/", we don't want another "skill-auditor/" layer
                    skill_name = skill["name"]
                    first_dir_to_strip = None
                    if entries:
                        first_entry = entries[0]
                        first_parts = list(filter(None, first_entry.split("/")))
                        if len(first_parts) >= 1 and first_parts[0] == skill_name:
                            first_dir_to_strip = skill_name

                    extracted_count = 0
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        # Normalize path separators for cross-platform compatibility
                        entry_name = info.filename.replace("\\", "/")
                        # Strip common prefix if all files are under one directory
                        if common_prefix:
                            entry_name = entry_name[len(common_prefix) + 1:]
                        # Also strip first directory if it matches skill name
                        if first_dir_to_strip:
                            entry_parts = list(filter(None, entry_name.split("/")))
                            if len(entry_parts) >= 1 and entry_parts[0] == first_dir_to_strip:
                                entry_name = "/".join(entry_parts[1:])
                        # Skip empty or directory-like entries
                        if not entry_name or entry_name.endswith("/") or entry_name.endswith("\\"):
                            continue
                        target = skill_dir / entry_name
                        # Skip if entry resolves to a directory path
                        if target.is_dir():
                            continue
                        target.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            target.write_bytes(zf.read(info.filename))
                            extracted_count += 1
                        except IsADirectoryError:
                            continue

                    if extracted_count == 0:
                        message = "警告: 压缩包内没有文件或提取失败"
                    else:
                        message = f"ZIP 已覆盖技能目录 ({extracted_count} 个文件)"
            else:
                # .tar, .tar.gz, .tgz, .tar.bz2, .tar.xz
                import tarfile
                with tarfile.open(fileobj=file_io, mode="r:*") as tf:
                    entries = [m.name.replace("\\", "/") for m in tf.getmembers() if not m.isdir()]
                    common_prefix = _flatten_single_top_level_dir(entries)

                    # Also strip first directory if it matches skill name
                    skill_name = skill["name"]
                    first_dir_to_strip = None
                    if entries:
                        first_entry = entries[0]
                        first_parts = list(filter(None, first_entry.split("/")))
                        if len(first_parts) >= 1 and first_parts[0] == skill_name:
                            first_dir_to_strip = skill_name

                    extracted_count = 0
                    for member in tf.getmembers():
                        if member.isdir():
                            continue
                        # Normalize path separators for cross-platform compatibility
                        entry_name = member.name.replace("\\", "/")
                        # Strip common prefix if all files are under one directory
                        if common_prefix:
                            entry_name = entry_name[len(common_prefix) + 1:]
                        # Also strip first directory if it matches skill name
                        if first_dir_to_strip:
                            entry_parts = list(filter(None, entry_name.split("/")))
                            if len(entry_parts) >= 1 and entry_parts[0] == first_dir_to_strip:
                                entry_name = "/".join(entry_parts[1:])
                        # Skip empty or directory-like entries
                        if not entry_name or entry_name.endswith("/") or entry_name.endswith("\\"):
                            continue
                        target = skill_dir / entry_name
                        # Skip if entry resolves to a directory path
                        if target.is_dir():
                            continue
                        target.parent.mkdir(parents=True, exist_ok=True)
                        extracted = tf.extractfile(member)
                        if extracted is not None:
                            try:
                                target.write_bytes(extracted.read())
                                extracted_count += 1
                            except IsADirectoryError:
                                continue

                    if extracted_count == 0:
                        message = "警告: 压缩包内没有文件或提取失败"
                    else:
                        message = f"压缩包已覆盖技能目录 ({extracted_count} 个文件)"
        else:
            # Single file - add/replace
            skill_dir.mkdir(parents=True, exist_ok=True)
            target = skill_dir / filename
            target.write_bytes(file_content)
            message = f"文件 {filename} 已上传"

        # Auto-generate .skill package
        try:
            package_path = _build_skill_package(skill["name"], skill["path"])
            message += f"，已生成安装包"
        except Exception as e:
            message += f"，但生成安装包失败: {str(e)}"

        # Mark skill as active after successful upload
        await skill_crud.update_status(conn, skill_id, "active")

    return redirect_with_message(f"/admin/skills/{skill_id}", message, "success")


@router.post("/skills/{skill_id}/update", response_class=HTMLResponse)
async def skill_update(
    request: Request,
    skill_id: int,
    admin_user: dict = Depends(require_admin),
    description: str = Form(""),
    dependencies: str = Form(""),
):
    """Update skill metadata (description and/or dependencies)."""
    deps = _parse_dependencies(dependencies) if dependencies else None

    async with get_db() as conn:
        skill = await skill_crud.get_by_id(conn, skill_id)
        if not skill:
            return redirect_with_message("/admin/skills", "技能不存在", "error")

        await skill_crud.update(
            conn,
            skill["name"],
            description=description if description else None,
            dependencies=deps,
        )

    return redirect_with_message(f"/admin/skills/{skill_id}", "技能信息已更新", "success")


@router.post("/skills/{skill_id}/delete", response_class=HTMLResponse)
async def skill_delete(request: Request, skill_id: int, admin_user: dict = Depends(require_admin)):
    """Delete a skill."""
    async with get_db() as conn:
        skill = await skill_crud.get_by_id(conn, skill_id)
        if not skill:
            return redirect_with_message("/admin/skills", "技能不存在", "error")

        await skill_crud.delete(conn, skill["name"])

        # Also delete .skill package
        package_path = _get_skill_package_path(skill["name"])
        if package_path:
            package_path.unlink()

    return redirect_with_message("/admin/skills", f"技能 '{skill['name']}' 已删除", "success")


@router.get("/skills/{skill_id}/download", response_class=Response)
async def skill_download(request: Request, skill_id: int, admin_user: dict = Depends(require_admin)):
    """Download skill as .skill package (ZIP format)."""
    async with get_db() as conn:
        skill = await skill_crud.get_by_id(conn, skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="技能不存在")

        # Check if package exists, if not build it
        package_path = _get_skill_package_path(skill["name"])
        if not package_path:
            try:
                package_path = _build_skill_package(skill["name"], skill["path"])
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="技能文件夹不存在，请先上传文件")

        # Use .zip extension so Windows can recognize and open it directly
        return Response(
            content=package_path.read_bytes(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{skill["name"]}.zip"'
            }
        )


@router.post("/skills/{skill_id}/rebuild-package", response_class=HTMLResponse)
async def skill_rebuild_package(request: Request, skill_id: int, admin_user: dict = Depends(require_admin)):
    """Rebuild .skill package for a skill."""
    async with get_db() as conn:
        skill = await skill_crud.get_by_id(conn, skill_id)
        if not skill:
            return redirect_with_message("/admin/skills", "技能不存在", "error")

        try:
            package_path = _build_skill_package(skill["name"], skill["path"])
            message = f"已重新生成 {skill['name']}.skill 包"
            message_type = "success"
        except FileNotFoundError:
            message = "技能文件夹不存在，请先上传文件"
            message_type = "error"
        except Exception as e:
            message = f"生成包失败: {str(e)}"
            message_type = "error"

    return redirect_with_message(f"/admin/skills/{skill_id}", message, message_type)


# ==================== Authorizations ====================

@router.get("/authorizations", response_class=HTMLResponse)
async def auth_list(request: Request, admin_user: dict = Depends(require_admin)):
    """List all authorizations."""
    async with get_db() as conn:
        users = await user_crud.list_users(conn, limit=1000)
        all_skills = await skill_crud.list_all(conn, limit=1000)
        # Only show active skills for grant
        skills = [s for s in all_skills if s.get("status") == "active"]

        # Build authorization matrix
        auths = []
        for user in users:
            user_skills = await user_skill_crud.get_user_skills(conn, user["id"])
            for us in user_skills:
                auths.append({
                    "user": user,
                    "skill": us,
                })

    return render_template("authorizations/list.html", {
        "request": request,
        "message": get_message(request),
        "auths": auths,
        "users": users,
        "skills": skills,
        "admin_user": admin_user,
    })


@router.post("/authorizations/grant", response_class=HTMLResponse)
async def auth_grant(
    request: Request,
    admin_user: dict = Depends(require_admin),
    user_id: int = Form(...),
    skill_id: int = Form(...),
):
    """Grant a skill to user (only active skills)."""
    async with get_db() as conn:
        skill = await skill_crud.get_by_id(conn, skill_id)
        if not skill:
            return redirect_with_message("/admin/authorizations", "技能不存在", "error")
        if skill.get("status") != "active":
            return redirect_with_message("/admin/authorizations", f"技能 '{skill['name']}' 尚未激活，无法授权", "error")

        await user_skill_crud.grant(conn, user_id, skill_id)

    return redirect_with_message("/admin/authorizations", "授权成功", "success")


@router.post("/authorizations/revoke", response_class=HTMLResponse)
async def auth_revoke(
    request: Request,
    admin_user: dict = Depends(require_admin),
    user_id: int = Form(...),
    skill_id: int = Form(...),
):
    """Revoke a skill from user."""
    async with get_db() as conn:
        await user_skill_crud.revoke(conn, user_id, skill_id)

    return redirect_with_message("/admin/authorizations", "已撤销授权", "success")


# ==================== Logs ====================

@router.get("/logs", response_class=HTMLResponse)
async def log_list(
    request: Request,
    admin_user: dict = Depends(require_admin),
    user_id: str = Query(default=None),
    skill_name: str = Query(default=None),
    status: str = Query(default=None),
    start_time: datetime = Query(default=None),
    end_time: datetime = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List call logs with filters."""
    # Convert user_id from string to int if provided
    user_id_int: Optional[int] = int(user_id) if user_id and user_id.isdigit() else None
    offset = (page - 1) * page_size

    async with get_db() as conn:
        logs, total = await call_log_crud.list_logs(
            conn,
            user_id=user_id_int,
            skill_name=skill_name,
            start_time=start_time,
            end_time=end_time,
            limit=page_size,
            offset=offset,
        )

        users = await user_crud.list_users(conn, limit=1000)
        skills = await skill_crud.list_all(conn, limit=1000)

    # Calculate stats for the filtered period
    async with get_db() as conn:
        all_logs, _ = await call_log_crud.list_logs(
            conn,
            user_id=user_id_int,
            skill_name=skill_name,
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

    success_count = sum(1 for log in all_logs if log.get("status") == "success")
    failure_count = sum(1 for log in all_logs if log.get("status") == "failure")
    denied_count = sum(1 for log in all_logs if log.get("status") == "denied")
    durations = [log.get("duration_ms", 0) for log in all_logs if log.get("duration_ms")]
    avg_duration = round(sum(durations) / len(durations)) if durations else 0

    return render_template("logs/list.html", {
        "request": request,
        "message": get_message(request),
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "filters": {
            "user_id": user_id,
            "skill_name": skill_name,
            "status": status,
            "start_time": start_time.isoformat() if start_time else "",
            "end_time": end_time.isoformat() if end_time else "",
        },
        "users": users,
        "skills": skills,
        "stats": {
            "total": total,
            "success": success_count,
            "failure": failure_count,
            "denied": denied_count,
            "avg_duration_ms": avg_duration,
        },
        "admin_user": admin_user,
    })