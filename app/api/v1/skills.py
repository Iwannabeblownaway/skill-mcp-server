"""Skill management API endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
import zipfile
import tarfile
import io
import re

from app.api.deps import verify_admin_api_key
from app.db.crud import skill as skill_crud
from app.db.crud.skill import SKILLS_DIR, load_skill_content
from app.db.session import get_db
from app.models.skill import SkillCreate, SkillUpdate, SkillResponse

router = APIRouter(prefix="/skills", tags=["skills"])


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


@router.post(
    "",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new skill",
)
async def create_new_skill(
    skill_data: SkillCreate,
    admin: dict = Depends(verify_admin_api_key),
) -> SkillResponse:
    """Create a new skill.

    Creates:
    1. Database record with skill metadata
    2. Skill folder with SKILL.md template
    """
    async with get_db() as conn:
        existing = await skill_crud.get_by_name(conn, skill_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Skill '{skill_data.name}' already exists",
            )

        # Use skill name as path if not provided
        skill_path = skill_data.name

        # Create skill folder and SKILL.md template
        skill_dir = SKILLS_DIR / skill_path
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
            path=skill_path,
            version=skill_data.version or "1.0",
        )

    return SkillResponse(**skill)


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
    "/{name}/files",
    status_code=status.HTTP_201_CREATED,
    summary="Upload skill file",
)
async def upload_skill_file(
    name: str,
    filename: str,
    file: UploadFile = File(...),
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """Upload a file to skill folder.

    Args:
        name: Skill name
        filename: Target filename (e.g., 'README.md', 'script.py')
        file: File content (multipart/form-data)
    """
    async with get_db() as conn:
        skill = await skill_crud.get_by_name(conn, name)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )

    # Ensure skill folder exists
    skill_dir = SKILLS_DIR / skill["path"]
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Write file
    file_path = skill_dir / filename
    content = await file.read()
    file_path.write_bytes(content)

    return {
        "name": name,
        "filename": filename,
        "size": len(content),
        "path": str(file_path.relative_to(SKILLS_DIR)),
    }


def _extract_archive(content: bytes, skill_dir: Path) -> list[str]:
    """Extract archive content to skill folder.

    Supports: .zip, .tar, .tar.gz, .tgz, .tar.bz2, .tar.xz, .gz, .bz2, .xz

    Returns list of extracted filenames.
    """
    extracted_files = []
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Try zip first
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            for file_info in zf.infolist():
                if file_info.is_dir():
                    continue
                filename = file_info.filename
                if "/" in filename or "\\" in filename:
                    filename = filename.split("/")[-1].split("\\")[-1]
                if filename:
                    (skill_dir / filename).write_bytes(zf.read(file_info.filename))
                    extracted_files.append(filename)
        return extracted_files

    # Try tar formats
    try:
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:*") as tf:
            for member in tf.getmembers():
                if member.isfile():
                    filename = member.name
                    if "/" in filename or "\\" in filename:
                        filename = filename.split("/")[-1].split("\\")[-1]
                    if filename:
                        (skill_dir / filename).write_bytes(
                            tf.extractfile(member).read()
                        )
                        extracted_files.append(filename)
            return extracted_files
    except tarfile.TarError:
        pass

    # Try single compressed file (.gz, .bz2, .xz without tar)
    filename = None
    if content[:2] == b"\x1f\x8b":  # gzip
        import gzip

        filename = "extracted_file"
        (skill_dir / filename).write_bytes(gzip.decompress(content))
        extracted_files.append(filename)
    elif content[:2] == b"BZ":  # bzip2
        import bz2

        filename = "extracted_file"
        (skill_dir / filename).write_bytes(bz2.decompress(content))
        extracted_files.append(filename)
    elif content[:2] == b"FD":  # xz
        import lzma

        filename = "extracted_file"
        (skill_dir / filename).write_bytes(lzma.decompress(content))
        extracted_files.append(filename)

    if not extracted_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported archive format. Supported: zip, tar, tar.gz, tgz, tar.bz2, tar.xz, gz, bz2, xz",
        )

    return extracted_files


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
    """Upload skill content - supports single file or archive.

    - Single SKILL.md: automatically wrapped into skills/{name}/SKILL.md
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
    is_archive = (
        zipfile.is_zipfile(io.BytesIO(content))
        or tarfile.is_tarfile(io.BytesIO(content))
        or filename.endswith(
            (
                ".tar.gz",
                ".tgz",
                ".tar.bz2",
                ".tar.xz",
                ".gz",
                ".bz2",
                ".xz",
                ".zip",
                ".tar",
                ".7z",
                ".skill",
            )
        )
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


@router.post(
    "",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create skill from file or archive",
)
async def create_skill_from_file(
    file: UploadFile = File(...),
    admin: dict = Depends(verify_admin_api_key),
) -> SkillResponse:
    """Create a new skill from upload.

    Skill name derived from filename (without extension).
    Supports: SKILL.md (wrapped in folder), .zip, .tar.gz, etc.
    """
    # Get skill name from filename
    filename = file.filename or "unknown"
    archive_extensions = (
        ".skill",
        ".zip",
        ".tar",
        ".tar.gz",
        ".tgz",
        ".tar.bz2",
        ".tar.xz",
    )

    for ext in archive_extensions:
        if filename.endswith(ext):
            skill_name = filename[: -len(ext)]
            break
    else:
        skill_name = filename

    # Sanitize name
    skill_name = re.sub(r"[^a-zA-Z0-9_-]", "_", skill_name)

    # Read content
    content = await file.read()

    async with get_db() as conn:
        # Check if exists
        existing = await skill_crud.get_by_name(conn, skill_name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Skill '{skill_name}' already exists",
            )

        skill_dir = SKILLS_DIR / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Check if it's an archive
        is_archive = (
            zipfile.is_zipfile(io.BytesIO(content))
            or tarfile.is_tarfile(io.BytesIO(content))
            or filename.endswith(archive_extensions)
        )

        if is_archive:
            _extract_archive(content, skill_dir)
            description = "Skill uploaded from archive"
        else:
            # Single file: wrap as SKILL.md
            (skill_dir / "SKILL.md").write_bytes(content)
            description = "Skill uploaded from file"

        # Create database record
        skill = await skill_crud.create(
            conn,
            name=skill_name,
            description=description,
            path=skill_name,
            version="1.0",
        )

    return SkillResponse(**skill)


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
    "/{name}/files/{filename}",
    summary="Download skill file",
)
async def download_skill_file(
    name: str,
    filename: str,
) -> FileResponse:
    """Download a file from skill folder."""
    from app.api.deps import get_current_user

    # Get current user (not admin, just authenticated)
    try:
        user = await get_current_user()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    async with get_db() as conn:
        skill = await skill_crud.get_by_name(conn, name)

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )

    skill_file = SKILLS_DIR / skill["path"] / filename
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
