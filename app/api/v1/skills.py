"""Skill management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import verify_admin_api_key
from app.db.crud import skill as skill_crud
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
    """List all skills."""
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
    """Create a new skill."""
    async with get_db() as conn:
        existing = await skill_crud.get_by_name(conn, skill_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Skill '{skill_data.name}' already exists",
            )

        skill = await skill_crud.create(
            conn,
            name=skill_data.name,
            description=skill_data.description,
            content=skill_data.content,
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
    """Update an existing skill."""
    async with get_db() as conn:
        skill = await skill_crud.update(
            conn,
            name=name,
            description=skill_data.description,
            content=skill_data.content,
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
    """Delete a skill."""
    async with get_db() as conn:
        deleted = await skill_crud.delete(conn, name)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' not found",
        )
