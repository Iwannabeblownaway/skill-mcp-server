"""Skill management API endpoints."""

from pathlib import Path
from typing import Optional, Dict
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
import zipfile
import tarfile
import io
import re

from app.api.deps import verify_admin_api_key, get_current_user
from app.db.crud import skill as skill_crud
from app.db.crud.skill import SKILLS_DIR, load_skill_content
from app.db.session import get_db
from app.models.skill import SkillCreate, SkillUpdate, SkillResponse
from app.services.skill_service import extract_urls_from_mcp_config

router = APIRouter(prefix="/skills", tags=["skills"])


def _extract_archive(content: bytes, skill_dir: Path) -> list[str]:
    """Extract archive content to skill folder.

    Supports: .zip, .tar, .tar.gz, .tgz, .tar.bz2, .tar.xz, .gz, .bz2, .xz

    Returns list of extracted filenames.
    Raises HTTPException on path traversal attempts.
    """
    extracted_files = []
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_dir_resolved = skill_dir.resolve()

    def _safe_extract(filename: str, write_func) -> bool:
        """Safely extract a file, validating path is within skill_dir.

        Returns True if extracted, False if skipped.
        Raises HTTPException on path traversal.
        """
        # Strip any path components - only allow filename
        if "/" in filename:
            filename = filename.split("/")[-1]
        if "\\" in filename:
            filename = filename.split("\\")[-1]

        # Reject empty or hidden filenames
        if not filename or filename.startswith("."):
            return False

        target_path = (skill_dir / filename).resolve()

        # Path traversal check: ensure resolved path is within skill_dir
        if not target_path.is_relative_to(skill_dir_resolved):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path traversal detected: {filename}",
            )

        write_func(target_path)
        extracted_files.append(filename)
        return True

    # Try zip first
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            for file_info in zf.infolist():
                if file_info.is_dir():
                    continue
                _safe_extract(
                    file_info.filename,
                    lambda p: p.write_bytes(zf.read(file_info.filename)),
                )
        return extracted_files

    # Try tar formats
    try:
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:*") as tf:
            for member in tf.getmembers():
                if member.isfile() and member.name:
                    extracted_content = tf.extractfile(member)
                    if extracted_content is None:
                        continue
                    _safe_extract(
                        member.name,
                        lambda p, c=extracted_content.read(): p.write_bytes(c),
                    )
            return extracted_files
    except tarfile.TarError:
        pass

    # Try single compressed file (.gz, .bz2, .xz without tar)
    filename = None
    if content[:2] == b"\x1f\x8b":  # gzip
        import gzip

        filename = "extracted_file"
        _safe_extract(filename, lambda p: p.write_bytes(gzip.decompress(content)))
    elif content[:2] == b"BZ":  # bzip2
        import bz2

        filename = "extracted_file"
        _safe_extract(filename, lambda p: p.write_bytes(bz2.decompress(content)))
    elif content[:2] == b"FD":  # xz
        import lzma

        filename = "extracted_file"
        _safe_extract(filename, lambda p: p.write_bytes(lzma.decompress(content)))

    if not extracted_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported archive format. Supported: zip, tar, tar.gz, tgz, tar.bz2, tar.xz, gz, bz2, xz",
        )

    return extracted_files


# ==================== List ====================


@router.get(
    "",
    summary="List all skills",
)
async def list_skills(
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """List all skills (metadata only, no content)."""
    async with get_db() as conn:
        skills = await skill_crud.list_all(conn)

    return {
        "skills": skills,
        "total": len(skills),
    }


# ==================== Create ====================


@router.post(
    "",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new skill from file",
)
async def create_skill_from_file(
    file: UploadFile = File(...),
    name: str = Query(..., description="Skill name (required)"),
    description: str = Query(
        ..., description="Skill description for tool listing (required)"
    ),
    mcp_config: Optional[str] = Query(
        None,
        description='JSON string of MCP server config (e.g., \'{"filesystem": {"url": "http://..."}}\')',
    ),
    admin: dict = Depends(verify_admin_api_key),
) -> SkillResponse:
    """Create a new skill from file upload.

    - name: Skill name (required)
    - description: Skill description for tool listing (required)
    - mcp_config: Optional JSON string of MCP server configuration
    - Single file: saved as SKILL.md in skills/{name}/
    - Archive (.zip, .tar.gz, etc.): extracted to skills/{name}/
    """
    skill_name = name
    # Sanitize
    skill_name = re.sub(r"[^a-zA-Z0-9_-]", "_", skill_name)

    # Parse mcp_config to extract dependencies
    dependencies = None
    if mcp_config:
        try:
            config = json.loads(mcp_config)
            dependencies = extract_urls_from_mcp_config(config)
        except (json.JSONDecodeError, Exception):
            pass  # Ignore invalid mcp_config

    content = await file.read()
    archive_exts = (
        ".skill",
        ".zip",
        ".tar",
        ".tar.gz",
        ".tgz",
        ".tar.bz2",
        ".tar.xz",
        ".gz",
        ".bz2",
        ".xz",
    )
    filename = file.filename or ""
    is_archive = (
        zipfile.is_zipfile(io.BytesIO(content))
        or tarfile.is_tarfile(io.BytesIO(content))
        or filename.lower().endswith(archive_exts)
    )

    async with get_db() as conn:
        existing = await skill_crud.get_by_name(conn, skill_name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Skill '{skill_name}' already exists",
            )

        skill_dir = SKILLS_DIR / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        if is_archive:
            _extract_archive(content, skill_dir)
        else:
            # Single file: save as SKILL.md
            (skill_dir / "SKILL.md").write_bytes(content)

        # Create database record
        skill = await skill_crud.create(
            conn,
            name=skill_name,
            description=description,
            path=skill_name,
            version="1.0",
            dependencies=dependencies,
        )

    return SkillResponse(**skill)


@router.post(
    "/json",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new skill from JSON",
)
async def create_skill_from_json(
    skill_data: SkillCreate,
    admin: dict = Depends(verify_admin_api_key),
) -> SkillResponse:
    """Create a new skill from JSON body.

    Creates:
    1. Database record with skill metadata
    2. Skill folder with SKILL.md template

    Optionally accepts mcp_config for dependency declaration.
    """
    # Extract dependencies from mcp_config if provided
    dependencies = None
    if skill_data.mcp_config:
        dependencies = extract_urls_from_mcp_config(skill_data.mcp_config)

    async with get_db() as conn:
        existing = await skill_crud.get_by_name(conn, skill_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Skill '{skill_data.name}' already exists",
            )

        # Create skill folder and SKILL.md template
        skill_dir = SKILLS_DIR / skill_data.name
        skill_file = skill_dir / "SKILL.md"
        readme_file = skill_dir / "README.md"

        skill_dir.mkdir(parents=True, exist_ok=True)

        # Create SKILL.md with template
        if not skill_file.exists():
            skill_file.write_text(
                f"# {skill_data.name}\n\n"
                f"## Description\n{skill_data.description}\n\n"
                f"## Usage\n\nDescribe how to use this skill...\n\n"
                f"## Examples\n\n```\nExample usage here...\n```\n",
                encoding="utf-8",
            )

        # Create README.md
        if not readme_file.exists():
            readme_file.write_text(
                f"# {skill_data.name}\n\n{skill_data.description}\n",
                encoding="utf-8",
            )

        # Create database record
        skill = await skill_crud.create(
            conn,
            name=skill_data.name,
            description=skill_data.description,
            path=skill_data.name,
            version=skill_data.version or "1.0",
            dependencies=dependencies,
        )

    return SkillResponse(**skill)


# ==================== Update ====================


@router.put(
    "/{name}",
    response_model=SkillResponse,
    summary="Update a skill",
)
async def update_existing_skill(
    name: str,
    skill_data: SkillUpdate,
    admin: dict = Depends(verify_admin_api_key),
) -> SkillResponse:
    """Update skill metadata (not content)."""
    async with get_db() as conn:
        skill = await skill_crud.update(
            conn,
            name=name,
            description=skill_data.description,
            version=skill_data.version,
        )

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )

    return SkillResponse(**skill)


class SkillContentUpdate(BaseModel):
    """Request model for updating skill content."""

    content: str


@router.put(
    "/{name}/content",
    summary="Update skill content",
)
async def update_skill_content(
    name: str,
    content_data: SkillContentUpdate,
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """Update skill SKILL.md content via API.

    Use this to upload or update the skill's SKILL.md content.
    """
    async with get_db() as conn:
        skill = await skill_crud.get_by_name(conn, name)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )

    # Write content to filesystem
    skill_file = skill_crud.get_skill_content_path(skill["path"])
    skill_file.parent.mkdir(parents=True, exist_ok=True)
    skill_file.write_text(content_data.content, encoding="utf-8")

    return {
        "name": name,
        "path": skill["path"],
        "content_length": len(content_data.content),
        "message": "Content updated successfully",
    }


@router.post(
    "/{name}/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload skill content (file or archive)",
)
async def upload_skill_content(
    name: str,
    file: UploadFile = File(...),
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """Upload skill content to existing skill - supports single file or archive.

    - Single SKILL.md: saved as skills/{name}/SKILL.md
    - Archive (.zip, .tar.gz, etc.): extracted to skills/{name}/
    """
    async with get_db() as conn:
        skill = await skill_crud.get_by_name(conn, name)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )

    content = await file.read()
    filename = file.filename or ""

    skill_dir = SKILLS_DIR / skill["path"]
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Detect if it's an archive
    archive_exts = (
        ".skill",
        ".zip",
        ".tar",
        ".tar.gz",
        ".tgz",
        ".tar.bz2",
        ".tar.xz",
        ".gz",
        ".bz2",
        ".xz",
    )
    is_archive = (
        zipfile.is_zipfile(io.BytesIO(content))
        or tarfile.is_tarfile(io.BytesIO(content))
        or filename.lower().endswith(archive_exts)
    )

    if is_archive:
        extracted_files = _extract_archive(content, skill_dir)
    else:
        # Single file: wrap into folder as SKILL.md
        target_filename = "SKILL.md"
        (skill_dir / target_filename).write_bytes(content)
        extracted_files = [target_filename]

    return {
        "name": name,
        "extracted_files": extracted_files,
        "file_count": len(extracted_files),
    }


# ==================== Sync ====================


@router.post(
    "/{name}/sync",
    summary="Sync skill from filesystem to database",
)
async def sync_skill_from_filesystem(
    name: str,
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """Sync skill content from filesystem folder to database JSON.

    Reads all files from skills/{name}/ folder and stores them as JSON in DB.
    Use this after editing skill files in the filesystem.
    """
    async with get_db() as conn:
        skill = await skill_crud.get_by_name(conn, name)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )

    # Load entire folder as JSON
    folder_content = skill_crud.load_skill_folder_as_json(skill["path"])
    if folder_content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill folder not found at {skill['path']}",
        )

    # Update database
    async with get_db() as conn:
        await skill_crud.update_content_json(conn, name, folder_content)

    file_count = len(folder_content)
    return {
        "name": name,
        "path": skill["path"],
        "files_synced": file_count,
        "files": list(folder_content.keys()),
        "message": f"Successfully synced {file_count} files from filesystem to database",
    }


# ==================== Delete ====================


@router.delete(
    "/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a skill",
)
async def delete_existing_skill(
    name: str,
    admin: dict = Depends(verify_admin_api_key),
) -> None:
    """Delete a skill (database record only, not filesystem)."""
    async with get_db() as conn:
        deleted = await skill_crud.delete(conn, name)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )


# ==================== Read ====================


@router.get(
    "/{name}/content",
    summary="Get skill content",
)
async def get_skill_content(
    name: str,
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """Get skill content from filesystem.

    Returns the SKILL.md content for the specified skill.
    """
    async with get_db() as conn:
        skill = await skill_crud.get_by_name(conn, name)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )

    content = load_skill_content(skill["path"])
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SKILL.md not found for skill '{name}'",
        )

    return {
        "name": name,
        "path": skill["path"],
        "content": content,
    }


@router.get(
    "/{name}/files",
    summary="List skill files",
)
async def list_skill_files(
    name: str,
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """List all files in skill folder."""
    async with get_db() as conn:
        skill = await skill_crud.get_by_name(conn, name)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )

    skill_dir = SKILLS_DIR / skill["path"]
    if not skill_dir.exists():
        return {"name": name, "files": []}

    files = [f.name for f in skill_dir.iterdir() if f.is_file()]
    return {"name": name, "files": files}


@router.get(
    "/{name}/dependencies",
    summary="Get skill MCP dependencies",
)
async def get_skill_dependencies(
    name: str,
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """Get MCP dependencies for a skill.

    Returns the list of MCP service URLs (base URLs without auth params)
    that this skill requires.
    """
    async with get_db() as conn:
        skill = await skill_crud.get_by_name(conn, name)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )

    dependencies = skill.get("dependencies", [])
    return {
        "name": name,
        "dependencies": dependencies,
    }


@router.get(
    "/{name}/files/{filename}",
    summary="Download skill file",
)
async def download_skill_file(
    name: str,
    filename: str,
    admin: dict = Depends(verify_admin_api_key),
) -> FileResponse:
    """Download a file from skill folder."""
    # Validate filename to prevent path traversal attacks
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: cannot contain path separators or '..'",
        )

    async with get_db() as conn:
        skill = await skill_crud.get_by_name(conn, name)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )

    skill_file = SKILLS_DIR / skill["path"] / filename
    # Verify the resolved path is still within SKILLS_DIR (defensive)
    if not skill_file.resolve().is_relative_to(SKILLS_DIR.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal detected",
        )
    if not skill_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found for skill '{name}'",
        )

    return FileResponse(
        path=str(skill_file),
        filename=filename,
        media_type="text/markdown"
        if filename.endswith(".md")
        else "application/octet-stream",
    )
