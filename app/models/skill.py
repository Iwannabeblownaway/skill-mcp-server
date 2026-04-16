"""Skill Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    """Model for creating a new skill."""

    name: str = Field(..., description="Unique skill name")
    description: str = Field(..., description="Skill description")
    content: str = Field(..., description="Skill content (markdown)")
    version: Optional[str] = Field("1.0", description="Skill version")


class SkillUpdate(BaseModel):
    """Model for updating an existing skill."""

    description: Optional[str] = Field(None, description="Skill description")
    content: Optional[str] = Field(None, description="Skill content")
    version: Optional[str] = Field(None, description="Skill version")


class SkillResponse(BaseModel):
    """Model for skill response."""

    id: int
    name: str
    description: str
    content: Optional[str] = None
    version: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SkillList(BaseModel):
    """Model for list of skills response."""

    skills: list
    total: int
    page: int
    page_size: int
