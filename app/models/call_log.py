"""CallLog Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CallLogResponse(BaseModel):
    """Model for call log response."""

    id: str = Field(..., description="Call log ID")
    user_id: str = Field(..., description="User ID who made the call")
    username: str = Field(..., description="Username who made the call")
    skill_id: str = Field(..., description="Skill ID that was called")
    skill_name: str = Field(..., description="Skill name that was called")
    tool_name: str = Field(..., description="Tool name that was invoked")
    status: str = Field(..., description="Call status (success/error)")
    request_payload: Optional[dict] = Field(None, description="Request payload")
    response_payload: Optional[dict] = Field(None, description="Response payload")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(
        None, description="Call duration in milliseconds"
    )
    created_at: datetime = Field(..., description="Call timestamp")


class CallLogList(BaseModel):
    """Model for list of call logs response."""

    logs: list[CallLogResponse] = Field(
        default_factory=list, description="List of call logs"
    )
    total: int = Field(..., description="Total number of call logs")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
