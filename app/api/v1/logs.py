"""Call log API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import verify_admin_api_key
from app.db.session import get_db
from app.db.crud import call_log as call_log_crud

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
    offset = (page - 1) * page_size

    async with get_db() as conn:
        logs, total = await call_log_crud.list_logs(
            conn,
            user_id=user_id,
            skill_name=skill_name,
            start_time=start_time,
            end_time=end_time,
            limit=page_size,
            offset=offset,
        )

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
