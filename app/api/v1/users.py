"""User management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import verify_admin_api_key
from app.db.crud import user as user_crud
from app.db.session import get_db
from app.models.user import UserCreate, UserWithKey

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserWithKey,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user with a generated API key. Returns the API key only once.",
)
async def create_new_user(
    user_data: UserCreate,
    admin: dict = Depends(verify_admin_api_key),
) -> UserWithKey:
    """Create a new user with generated API key."""
    async with get_db() as conn:
        user = await user_crud.create(
            conn,
            user_id=user_data.user_id,
            username=user_data.username,
            role=user_data.role or "user",
        )

    return UserWithKey(
        id=user["id"],
        user_id=user["user_id"],
        username=user["username"],
        api_key=user["api_key"],
        role=user["role"],
    )


@router.get(
    "",
    summary="List users",
    description="Get a list of all users.",
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: dict = Depends(verify_admin_api_key),
) -> dict:
    """List all users with pagination."""
    offset = (page - 1) * page_size
    async with get_db() as conn:
        users = await user_crud.list_users(conn, limit=page_size, offset=offset)

    return {
        "users": users,
        "total": len(users),
        "page": page,
        "page_size": page_size,
    }
