"""MCP Server implementation with Streamable HTTP transport.

This module provides:
- MCP Server instance creation using mcp.server.Server
- StreamableHTTP session manager for HTTP transport
- Auth middleware for API key validation (via query param only)

Based on MCP Python SDK streamable_http transport.
"""

import logging
from contextvars import ContextVar
from typing import Any

from starlette.requests import Request
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool as MCPTool

from app.services.user_service import verify_api_key

# Configure logging
logger = logging.getLogger(__name__)

# Context variable to store current user for async handlers
current_user: ContextVar[dict | None] = ContextVar("current_user", default=None)

# Create the MCP server instance
mcp_server = Server("skill_mcp")


async def auth_middleware(scope, receive, send, next_handler):
    """ASGI middleware that validates API key for /mcp/* routes.

    Skips auth for non-/mcp routes so other endpoints work normally.
    Uses root_path to detect mounted MCP routes since FastAPI strips the prefix.
    Only checks ?key= query param (common MCP pattern).
    """
    request = Request(scope, receive)

    # Check if this is an MCP request:
    # - path starts with /mcp (direct access)
    # - OR root_path is /mcp (FastAPI mount strips prefix from path)
    path = request.url.path
    root_path = scope.get("root_path", "")
    is_mcp_route = path.startswith("/mcp") or root_path == "/mcp"

    if not is_mcp_route:
        return await next_handler(scope, receive, send)

    # Allow GET requests to pass through (used for SSE stream establishment)
    method = scope.get("method", "")
    if method == "GET":
        return await next_handler(scope, receive, send)

    # Extract API key from query param only (common MCP pattern)
    api_key = request.query_params.get("key")

    if not api_key:
        from starlette.responses import JSONResponse

        response = JSONResponse(
            {"error": "Missing API key. Provide via ?key= query param"},
            status_code=401,
        )
        await response(scope, receive, send)
        return

    # Verify API key against database
    user = await verify_api_key(api_key.strip())
    if user is None:
        from starlette.responses import JSONResponse

        response = JSONResponse({"error": "Invalid API key"}, status_code=401)
        await response(scope, receive, send)
        return

    # Store user in request state and context variable for downstream use
    request.state.user = user
    current_user.set(user)

    # Continue to next handler
    return await next_handler(scope, receive, send)


# Create session manager for Streamable HTTP
# Using stateless=True for simplicity (no session persistence needed)
# json_response=True so client only needs to accept application/json (not SSE)
session_manager = StreamableHTTPSessionManager(
    app=mcp_server,
    stateless=True,
    json_response=True,
)


# ASGI app that combines auth middleware + session manager
async def mcp_asgi_handler(scope, receive, send):
    """ASGI handler that validates auth and routes to session manager."""

    async def next_handler(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)

    await auth_middleware(scope, receive, send, next_handler)


# Expose for external mounting (e.g., in main.py)
def get_mcp_asgi_handler():
    """Return the MCP ASGI handler with auth middleware."""
    return mcp_asgi_handler


def get_session_manager() -> StreamableHTTPSessionManager:
    """Get the session manager instance."""
    return session_manager


@mcp_server.list_tools()
async def list_tools() -> list[MCPTool]:
    """Handle tools/list MCP method.

    Returns the list of tools (skills) available to the authenticated user.
    The tools are dynamically fetched from the database and filtered by user permissions.

    Returns:
        List of MCP Tool objects representing available skills.
    """
    from app.db.session import get_db
    from app.db.crud import skill as skill_crud
    from app.db.crud import user_skill as user_skill_crud

    logger.info("list_tools called")
    try:
        # Get current user from context
        user = current_user.get()
        user_id = user.get("id") if user else None

        async with get_db() as conn:
            logger.info("DB connection acquired, fetching skills")
            if user_id:
                # Fetch only user's authorized skills
                user_skills = await user_skill_crud.get_user_skills(conn, user_id)
                skill_ids = [s["id"] for s in user_skills]
                if skill_ids:
                    all_skills = await skill_crud.get_by_ids(conn, skill_ids)
                else:
                    all_skills = []
            else:
                # No user context, return empty
                all_skills = []
            logger.info(f"Found {len(all_skills)} skills for user {user_id}")

        tools = []
        for skill in all_skills:
            tool = MCPTool(
                name=f"use_skill_{skill['name']}",
                description=skill.get(
                    "description", f"Execute the {skill['name']} skill"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "The name of the skill to invoke",
                        },
                    },
                    "required": ["skill_name"],
                },
            )
            tools.append(tool)

        logger.info(f"Returning {len(tools)} tools")
        return tools
    except Exception as e:
        logger.error(f"Error listing tools: {e}", exc_info=True)
        return []


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tools/call MCP method.

    Executes the requested tool (skill) and returns the result.
    Tool names starting with 'use_skill_' invoke the corresponding skill.

    Args:
        name: The name of the tool to call.
        arguments: Arguments passed to the tool.

    Returns:
        List of TextContent with the tool execution result.
    """
    from app.services.skill_service import get_skill_content as svc_get_skill_content

    # Extract skill name from tool name
    if name.startswith("use_skill_"):
        skill_name = name[len("use_skill_") :]
    else:
        skill_name = name

    # Get skill_name from arguments if provided
    skill_name = arguments.get("skill_name", skill_name)

    if not skill_name:
        return [TextContent(type="text", text="Error: Skill name is required")]

    # Get current user from context
    user = current_user.get()
    user_id = user.get("id") if user else None

    try:
        content, error = await svc_get_skill_content(
            user_id=user_id, skill_name=skill_name
        )
        if error:
            return [TextContent(type="text", text=f"Error: {error}")]
        return [TextContent(type="text", text=content)]
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@mcp_server.list_resources()
async def list_resources() -> list:
    """Handle resources/list MCP method.

    This server does not expose any resources.

    Returns:
        Empty list.
    """
    return []


@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    """Handle resources/read MCP method.

    This server does not support resource reading.

    Args:
        uri: Resource URI to read.

    Returns:
        Error message.
    """
    return f"Error: Resource reading not supported. URI: {uri}"


@mcp_server.list_prompts()
async def list_prompts() -> list:
    """Handle prompts/list MCP method.

    This server does not expose any prompts.

    Returns:
        Empty list.
    """
    return []


@mcp_server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, Any] | None) -> str:
    """Handle prompts/get MCP method.

    This server does not support prompt retrieval.

    Args:
        name: Prompt name.
        arguments: Optional prompt arguments.

    Returns:
        Error message.
    """
    return f"Error: Prompt retrieval not supported. Name: {name}"


def get_mcp_server() -> Server:
    """Get the MCP Server instance.

    Returns:
        The configured MCP Server instance.
    """
    return mcp_server
