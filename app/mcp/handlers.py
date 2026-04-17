"""MCP protocol handlers for list_tools and call_tool operations.

This module implements the MCP protocol handlers that:
- list_tools: Returns user's authorized skills as MCP Tool list
- call_tool: Handles use_skill_xxx tool calls and invokes skill content retrieval
"""

import time
from typing import Any

from mcp.types import Tool, TextContent

from app.services.skill_service import get_user_skills, get_skill_content, log_call
from app.mcp.session import get_user_id_from_session


# Tool name prefix for skill tools
SKILL_TOOL_PREFIX = "use_skill_"

# JSON Schema for skill tool input
SKILL_TOOL_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "skill_name": {
            "type": "string",
            "description": "The name of the skill to invoke",
        },
        "parameters": {
            "type": "object",
            "description": "Optional parameters for the skill execution",
            "default": {},
        },
    },
    "required": ["skill_name"],
}


async def handle_list_tools(session_id: str) -> list[Tool]:
    """Handle the list_tools MCP request.

    Retrieves the user's authorized skills and returns them as
    a list of MCP Tool objects, each representing a skill that
    can be invoked via call_tool.

    Args:
        session_id: The active MCP session ID.

    Returns:
        A list of Tool objects representing user's authorized skills.
    """
    user_id = await get_user_id_from_session(session_id)

    if user_id is None:
        # Return empty list if no valid session
        return []

    # Get user's authorized skills
    skills = await get_user_skills(user_id)

    # Convert skills to MCP Tool objects
    tools = []
    for skill in skills:
        description = skill.get("description", f"Execute the {skill['name']} skill")
        dependencies = skill.get("dependencies", [])

        # Add MCP requirements hint to description if skill has dependencies
        if dependencies:
            deps_hint = (
                "\n\n[MCP Requirements] This skill requires the following MCP services: "
                + ", ".join(dependencies)
                + ". Please ensure these services are configured in your MCP client."
            )
            description = description + deps_hint

        tool = Tool(
            name=f"{SKILL_TOOL_PREFIX}{skill['name']}",
            description=description,
            inputSchema=SKILL_TOOL_INPUT_SCHEMA,
        )
        tools.append(tool)

    return tools


async def handle_call_tool(
    session_id: str, tool_name: str, arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle the call_tool MCP request.

    Processes tool calls for use_skill_xxx tools, invokes the
    corresponding skill, and logs the call.

    Args:
        session_id: The active MCP session ID.
        tool_name: The name of the tool being called.
        arguments: The tool arguments provided by the client.

    Returns:
        A list of TextContent objects containing the result or error message.
    """
    user_id = await get_user_id_from_session(session_id)

    if user_id is None:
        return [
            TextContent(
                type="text",
                text="Error: Invalid or expired session. Please reconnect.",
            )
        ]

    # Check if this is a skill tool call
    if not tool_name.startswith(SKILL_TOOL_PREFIX):
        return [
            TextContent(
                type="text",
                text=f"Error: Unknown tool '{tool_name}'. Only skill tools ({SKILL_TOOL_PREFIX}*) are supported.",
            )
        ]

    # Extract skill name from tool name
    skill_name = tool_name[len(SKILL_TOOL_PREFIX) :]

    if not skill_name:
        return [
            TextContent(
                type="text",
                text="Error: Invalid skill tool name. Skill name cannot be empty.",
            )
        ]

    # Track call duration
    start_time = time.time()

    try:
        # Get skill content
        content, error = await get_skill_content(user_id, skill_name)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log the call
        if error:
            await log_call(
                user_id=user_id,
                skill_name=skill_name,
                status="error",
                error_msg=error,
                duration_ms=duration_ms,
            )
            return [
                TextContent(
                    type="text",
                    text=f"Error executing skill '{skill_name}': {error}",
                )
            ]

        # Log successful call
        await log_call(
            user_id=user_id,
            skill_name=skill_name,
            status="success",
            error_msg="",
            duration_ms=duration_ms,
        )

        # Return the skill content
        return [
            TextContent(
                type="text",
                text=content,
            )
        ]

    except Exception as e:
        # Calculate duration even on exception
        duration_ms = int((time.time() - start_time) * 1000)

        # Log the error
        await log_call(
            user_id=user_id,
            skill_name=skill_name,
            status="error",
            error_msg=str(e),
            duration_ms=duration_ms,
        )

        return [
            TextContent(
                type="text",
                text=f"Error executing skill '{skill_name}': {str(e)}",
            )
        ]


async def handle_list_resources() -> list:
    """Handle the list_resources MCP request.

    Returns an empty list as this server does not expose resources.

    Returns:
        Empty list of resources.
    """
    return []


async def handle_read_resource(uri: str) -> str:
    """Handle the read_resource MCP request.

    Returns an error as this server does not support resource reading.

    Args:
        uri: The resource URI to read.

    Returns:
        Error message string.
    """
    return f"Error: Resource reading not supported. URI: {uri}"


async def handle_list_prompts() -> list:
    """Handle the list_prompts MCP request.

    Returns an empty list as this server does not expose prompts.

    Returns:
        Empty list of prompts.
    """
    return []


async def handle_get_prompt(name: str, arguments: dict[str, Any] | None) -> str:
    """Handle the get_prompt MCP request.

    Returns an error as this server does not support prompt retrieval.

    Args:
        name: The prompt name.
        arguments: Optional prompt arguments.

    Returns:
        Error message string.
    """
    return f"Error: Prompt retrieval not supported. Name: {name}"
