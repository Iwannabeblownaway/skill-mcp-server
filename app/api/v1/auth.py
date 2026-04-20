"""User-skill authorization API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import verify_admin_api_key
from app.db.crud import user_skill as user_skill_crud
from app.db.crud import skill as skill_crud
from app.db.crud import user as user_crud
from app.db.session import get_db
from app.models.user_skill import UserSkillGrant

router = APIRouter(prefix="/user_skills", tags=["authorization"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Grant a skill to a user",
)
async def grant_skill(
    grant_data: UserSkillGrant,
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """Grant a skill to a user."""
    async with get_db() as conn:
        user = await user_crud.get_by_id(conn, grant_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {grant_data.user_id} not found",
            )

        skill = await skill_crud.get_by_id(conn, grant_data.skill_id)
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill {grant_data.skill_id} not found",
            )

        if skill.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Skill '{skill['name']}' is not active (draft status)",
            )

        granted = await user_skill_crud.grant(
            conn, grant_data.user_id, grant_data.skill_id
        )

    return {
        "granted": granted,
        "user_id": grant_data.user_id,
        "skill_id": grant_data.skill_id,
    }


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a skill from a user",
)
async def revoke_skill(
    user_id: int,
    skill_id: int,
    admin: dict = Depends(verify_admin_api_key),
) -> None:
    """Revoke a skill from a user."""
    async with get_db() as conn:
        revoked = await user_skill_crud.revoke(conn, user_id, skill_id)

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User-skill association not found",
        )
