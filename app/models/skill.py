"""Skill Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    """Model for creating a new skill."""

    name: str = Field(..., description="Unique skill name")
    description: str = Field(..., description="Skill description")
    version: Optional[str] = Field("1.0", description="Skill version")
    mcp_config: Optional[dict] = Field(
        None, description="MCP server configuration for dependencies"
    )
    # Skill content is stored in filesystem, not in database


class SkillUpdate(BaseModel):
    """Model for updating an existing skill."""

    description: Optional[str] = Field(None, description="Skill description")
    version: Optional[str] = Field(None, description="Skill version")
    # Content updates go to filesystem directly


class SkillResponse(BaseModel):
    """Model for skill response."""

    id: int
    name: str
    description: str
    path: str  # Relative path to skill folder
    version: str
    dependencies: Optional[list[str]] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SkillList(BaseModel):
    """Model for list of skills response."""

    skills: list
    total: int
    page: int
    page_size: int
