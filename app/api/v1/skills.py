"""Skill management API endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

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


@router.get(
    "/{name}/file",
    summary="Download skill file",
)
async def download_skill_file(
    name: str,
) -> FileResponse:
    """Download the SKILL.md file directly."""
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

    skill_file = skill_crud.get_skill_content_path(skill["path"])
    if not skill_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SKILL.md not found for skill '{name}'",
        )

    return FileResponse(
        path=str(skill_file),
        filename=f"{name}.md",
        media_type="text/markdown",
    )
