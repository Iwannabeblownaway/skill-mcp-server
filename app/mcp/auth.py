"""MCP authentication module for API key extraction and verification.

This module handles authentication for MCP connections by extracting
and verifying API keys from HTTP request headers.
"""

from typing import Optional
from fastapi import Request, HTTPException, status

from app.services.user_service import verify_api_key


# Header name for API key extraction
API_KEY_HEADER = "X-API-Key"


async def extract_api_key(request: Request) -> str:
    """Extract API key from the request headers or query params.

    Args:
        request: The FastAPI request object.

    Returns:
        The API key string.

    Raises:
        HTTPException: If the API key is missing or empty.
    """
    # Try header first
    api_key = request.headers.get(API_KEY_HEADER)

    # Fallback to query parameter (for MCP clients that pass key in URL)
    if not api_key:
        api_key = request.query_params.get("key")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing API key. Provide via {API_KEY_HEADER} header or ?key= query param",
        )

    if not api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty API key",
        )

    return api_key.strip()


async def authenticate_mcp_connection(request: Request) -> dict:
    """Authenticate an MCP connection request.

    Extracts the API key from headers and verifies it against
    the user database.

    Args:
        request: The FastAPI request object containing headers.

    Returns:
        User dictionary containing user details (id, user_id, username, role, etc.).

    Raises:
        HTTPException: If authentication fails (invalid or missing API key).
    """
    api_key = await extract_api_key(request)

    user = await verify_api_key(api_key)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return user


async def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from request without raising exceptions.

    This is a softer version of authenticate_mcp_connection that
    returns None instead of raising exceptions.

    Args:
        request: The FastAPI request object.

    Returns:
        User dictionary if authenticated, None otherwise.
    """
    try:
        return await authenticate_mcp_connection(request)
    except HTTPException:
        return None
