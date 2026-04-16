"""UserSkill Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserSkillGrant(BaseModel):
    """Model for granting a skill to a user."""

    user_id: int = Field(..., description="User ID to grant skill to")
    skill_id: int = Field(..., description="Skill ID to grant")


class UserSkillResponse(BaseModel):
    """Model for user-skill relationship response."""

    user_id: int
    skill_id: int
    granted_at: datetime
