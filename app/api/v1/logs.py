"""Call log API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import verify_admin_api_key
from app.db.session import get_db

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get(
    "",
    summary="List call logs",
)
async def list_call_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    skill_name: Optional[str] = Query(None, description="Filter by skill name"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """List call logs with optional filters."""
    return {
        "logs": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
    }
