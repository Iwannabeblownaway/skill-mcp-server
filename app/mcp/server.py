"""MCP Server implementation with Streamable HTTP transport.

This module provides:
- MCP Server instance creation using mcp.server.Server
- StreamableHTTP session manager for HTTP transport
- Auth middleware for API key validation (via query param only)

Based on MCP Python SDK streamable_http transport.
"""

import logging
from contextvars import ContextVar
from typing import Any, Iterable

from starlette.requests import Request
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool as MCPTool, GetPromptResult

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

    # Extract API key from header (more secure than URL query param)
    # Fall back to query param for backward compatibility
    api_key = request.headers.get("X-API-Key") or request.query_params.get("key")

    if not api_key:
        from starlette.responses import JSONResponse

        response = JSONResponse(
            {
                "error": "Missing API key. Provide via X-API-Key header or ?key= query param"
            },
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

        # Add global index/file tools (always available)
        tools.append(
            MCPTool(
                name="get_skill_index",
                description="[SKILL] 获取skill的文件索引（文件名和大小，不含内容）。使用此工具获取skill的文件结构，然后按需获取单个文件。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "Skill名称",
                        },
                    },
                    "required": ["skill_name"],
                },
            )
        )

        tools.append(
            MCPTool(
                name="get_skill_file",
                description="[SKILL] 读取skill指定文件的内容。须先调用get_skill_index获取文件列表。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "Skill名称",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "文件路径（相对于skill根目录），如'SKILL.md'或'references/template.md'",
                        },
                    },
                    "required": ["skill_name", "file_path"],
                },
            )
        )

        # Add per-skill tools (for backward compatibility, returns full folder)
        for skill in all_skills:
            skill_name = skill["name"]
            skill_desc = skill.get("description", f"Execute the {skill_name} skill")

            tools.append(
                MCPTool(
                    name=f"get_skill_{skill_name}",
                    description=f"[SKILL: {skill_name}] {skill_desc}",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "skill_name": {
                                "type": "string",
                                "description": f"Skill name (auto-filled: {skill_name})",
                            },
                        },
                        "required": [],
                    },
                )
            )

        logger.info(f"Returning {len(tools)} tools")
        return tools
    except Exception as e:
        logger.error(f"Error listing tools: {e}", exc_info=True)
        raise  # Re-raise so MCP framework returns error response to client


async def _get_skill_dependencies(skill_name: str) -> list[str]:
    """Fetch dependencies for a skill from the database."""
    from app.db.session import get_db
    from app.db.crud import skill as skill_crud

    try:
        async with get_db() as conn:
            sk = await skill_crud.get_by_name(conn, skill_name)
            return sk.get("dependencies", []) if sk else []
    except Exception:
        return []


# Client detection patterns for MCP config paths
MCP_CONFIG_PATTERNS = {
    "opencode": {
        "files": [
            "~/.opencode.json",
            "~/.config/opencode/opencode.json",
            "%USERPROFILE%/.opencode.json",
            "%LOCALAPPDATA%/opencode/.opencode.json",
            ".opencode.json",
            "~/.config/opencode/mcp/*.json",
            ".opencode/mcp/*.json",
            "~/.claude/.mcp.json",
            ".mcp.json",
        ],
        "search_key": "mcp",
        "format": "JSON",
        "cli_check": "opencode mcp list",
    },
    "claude-code": {
        "files": [
            "~/.claude.json",  # NOTE: outside ~/.claude/ directory!
            ".mcp.json",
            "~/.claude/settings.json",
        ],
        "search_key": "mcpServers",
        "format": "JSON",
        "cli_check": "claude mcp list",
    },
    "claude-desktop": {
        "files": [
            "~/Library/Application Support/Claude/claude_desktop_config.json",
            "%APPDATA%/Claude/claude_desktop_config.json",
            "~/.config/Claude/claude_desktop_config.json",
        ],
        "search_key": "mcpServers",
        "format": "JSON",
        "cli_check": None,
    },
    "openclaw": {
        "files": [
            "~/.openclaw/openclaw.json",
        ],
        "search_key": "mcpServers",
        "format": "JSON",
        "cli_check": "openclaw mcp list",
    },
    "cursor": {
        "files": [
            "~/.cursor/mcp.json",
            ".cursor/mcp.json",
        ],
        "search_key": "mcpServers",
        "format": "JSON",
        "cli_check": None,
    },
    "codex": {
        "files": [
            "~/.codex/config.toml",
        ],
        "search_key": "mcp_servers",
        "format": "TOML",
        "cli_check": None,
    },
    "cline": {
        "files": [
            "~/.cline/mcp_settings.json",
        ],
        "search_key": "mcpServers",
        "format": "JSON",
        "cli_check": None,
    },
    "continue": {
        "files": [
            "~/.continue/config.json",
        ],
        "search_key": "mcpServers",
        "format": "JSON (array)",
        "cli_check": None,
    },
}


def _build_config_check_instructions(deps: list[str]) -> str:
    """Build detailed MCP config check instructions for AI clients."""

    instructions = [
        "\n\n[MCP Requirements] This skill requires the following MCP services: "
        + ", ".join(deps)
        + ".\n",
        "=" * 60,
        "HOW TO CHECK AND CONFIGURE MCP DEPENDENCIES",
        "=" * 60,
        "\n## Step 1: Search for MCP Config Files\n",
        "Search the following locations for MCP configuration files:\n",
    ]

    # Collect all unique file patterns
    all_files = set()
    for client_info in MCP_CONFIG_PATTERNS.values():
        all_files.update(client_info["files"])

    # Group by directory for readability
    for pattern in sorted(all_files):
        instructions.append(f"  - `{pattern}`")

    instructions.extend(
        [
            "\n## Step 2: Parse MCP Configuration\n",
            "Read any found config file and look for:\n",
            "  - `mcp` or `mcpServers` or `mcp_servers` field\n",
            "  - Remote MCP URLs (http/https)\n",
            "  - Local MCP commands (npx, python, node)\n",
        ]
    )

    instructions.append("\n## Step 3: Client-Specific Config Locations\n")

    for client_name, info in MCP_CONFIG_PATTERNS.items():
        instructions.append(f"\n### {client_name.upper()}")
        instructions.append(f"  Config file(s):")
        for f in info["files"]:
            instructions.append(f"    - `{f}`")
        instructions.append(f"  Format: {info['format']}")
        instructions.append(f"  Search key: `{info['search_key']}`")
        if info["cli_check"]:
            instructions.append(f"  CLI check: `{info['cli_check']}`")

    instructions.extend(
        [
            "\n## Step 4: Example Remote MCP Config\n",
            "For a remote HTTP MCP server (like Sorftime), add this to your config:\n",
            "```json\n",
            "{\n",
            '  "mcpServers": {\n',
            '    "sorftime": {\n',
            '      "type": "remote",\n',
            '      "url": "https://mcp.sorftime.com",\n',
            '      "headers": {\n',
            '        "Authorization": "Bearer YOUR_API_KEY"\n',
            "      }\n",
            "    }\n",
            "  }\n",
            "}\n",
            "```\n",
            "\n## Step 5: Verify Configuration\n",
            "After adding the MCP config, verify by checking if the required tools are available.\n",
        ]
    )

    return "\n".join(instructions)


def _append_deps_warning(skill_name: str, deps: list[str], content: str) -> str:
    """Prepend MCP dependencies warning with detailed config instructions."""
    if not deps:
        return content
    warning = _build_config_check_instructions(deps)
    return warning + content


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tools/call MCP method.

    Supports:
    - get_skill_index: Returns skill file index (path -> size, no content)
    - get_skill_file: Returns content of a single file from skill folder
    - get_skill_{name}: Returns full skill folder as JSON (for backward compatibility)

    Args:
        name: The name of the tool to call.
        arguments: Arguments passed to the tool.

    Returns:
        List of TextContent with the tool execution result.
    """
    import time
    import json

    from app.services.skill_service import (
        get_skill_content_json as svc_get_skill_content_json,
        get_skill_index as svc_get_skill_index,
        get_skill_file as svc_get_skill_file,
        log_call as svc_log_call,
    )

    # Get current user from context
    user = current_user.get()
    user_id = user.get("id") if user else None

    # If no user, return error (should not happen if auth middleware works)
    if user_id is None:
        return [TextContent(type="text", text="Error: Authentication required")]

    # Track timing and determine skill name for logging
    start_time = time.time()
    skill_name = None
    status = "success"
    error_msg = None

    try:
        if name == "get_skill_index":
            skill_name = arguments.get("skill_name", "")
            if not skill_name:
                error_msg = "skill_name is required"
                status = "failure"
                return [TextContent(type="text", text=f"Error: {error_msg}")]
            try:
                index_data, error = await svc_get_skill_index(
                    user_id=user_id, skill_name=skill_name
                )
                if error:
                    error_msg = error
                    status = "failure"
                    return [TextContent(type="text", text=f"Error: {error}")]
                deps = await _get_skill_dependencies(skill_name)
                json_str = json.dumps(index_data, ensure_ascii=False, indent=2)
                result = _append_deps_warning(skill_name, deps, json_str)
                return [TextContent(type="text", text=result)]
            except Exception as e:
                logger.error(f"Error calling get_skill_index: {e}")
                error_msg = str(e)
                status = "failure"
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        elif name == "get_skill_file":
            skill_name = arguments.get("skill_name", "")
            file_path = arguments.get("file_path", "")
            if not skill_name:
                error_msg = "skill_name is required"
                status = "failure"
                return [TextContent(type="text", text=f"Error: {error_msg}")]
            if not file_path:
                error_msg = "file_path is required"
                status = "failure"
                return [TextContent(type="text", text=f"Error: {error_msg}")]
            try:
                content, error = await svc_get_skill_file(
                    user_id=user_id, skill_name=skill_name, file_path=file_path
                )
                if error:
                    error_msg = error
                    status = "failure"
                    return [TextContent(type="text", text=f"Error: {error}")]
                if content is None:
                    error_msg = "Failed to load skill file content"
                    status = "failure"
                    return [TextContent(type="text", text=f"Error: {error_msg}")]
                deps = await _get_skill_dependencies(skill_name)
                result = _append_deps_warning(skill_name, deps, content)
                return [TextContent(type="text", text=result)]
            except Exception as e:
                logger.error(f"Error calling get_skill_file: {e}")
                error_msg = str(e)
                status = "failure"
                return [TextContent(type="text", text=f"Error: {error_msg}")]

        else:
            # Legacy: get_skill_{name} - returns full folder JSON
            if name.startswith("get_skill_"):
                skill_name = name[len("get_skill_") :]
            else:
                skill_name = name

            skill_name = arguments.get("skill_name", skill_name)

            if not skill_name:
                error_msg = "Skill name is required"
                status = "failure"
                return [TextContent(type="text", text=f"Error: {error_msg}")]

            try:
                content_json, error = await svc_get_skill_content_json(
                    user_id=user_id, skill_name=skill_name
                )
                if error:
                    error_msg = error
                    status = "failure"
                    return [TextContent(type="text", text=f"Error: {error}")]
                deps = await _get_skill_dependencies(skill_name)
                json_str = json.dumps(content_json, ensure_ascii=False, indent=2)
                result = _append_deps_warning(skill_name, deps, json_str)
                return [TextContent(type="text", text=result)]
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                error_msg = str(e)
                status = "failure"
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    finally:
        # Always log the call, even on errors
        if skill_name and user_id:
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                await svc_log_call(
                    user_id=user_id,
                    skill_name=skill_name,
                    status=status,
                    error_msg=error_msg or "",
                    duration_ms=duration_ms,
                )
            except Exception as e:
                logger.error(f"Failed to log skill call: {e}")


@mcp_server.list_resources()
async def list_resources() -> list:
    """Handle resources/list MCP method.

    This server does not expose any resources.

    Returns:
        Empty list.
    """
    return []


@mcp_server.read_resource()
async def read_resource(uri: Any) -> Any:
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
async def get_prompt(name: str, arguments: dict[str, Any] | None) -> GetPromptResult:
    """Handle prompts/get MCP method.

    This server does not support prompt retrieval.

    Args:
        name: Prompt name.
        arguments: Optional prompt arguments.

    Returns:
        Never returns - always raises NotImplementedError.
    Raises:
        NotImplementedError: Prompt retrieval is not supported.
    """
    raise NotImplementedError(f"Prompt retrieval not supported. Name: {name}")


def get_mcp_server() -> Server:
    """Get the MCP Server instance.

    Returns:
        The configured MCP Server instance.
    """
    return mcp_server
