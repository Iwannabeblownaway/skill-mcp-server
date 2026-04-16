"""User Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Model for creating a new user."""

    user_id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="User display name")
    role: Optional[str] = Field("user", description="User role (admin or user)")


class UserResponse(BaseModel):
    """Model for user response (without sensitive data)."""

    id: int
    user_id: str
    username: str
    role: str
    created_at: datetime


class UserWithKey(BaseModel):
    """Model for user response including API key (for initial creation)."""

    id: int
    user_id: str
    username: str
    api_key: str
    role: str


class UserList(BaseModel):
    """Model for list of users response."""

    users: list[UserResponse]
    total: int
    page: int
    page_size: int
