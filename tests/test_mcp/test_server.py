"""Tests for MCP server module (app.mcp.server)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

from app.mcp.server import (
    call_tool,
    list_tools,
    _get_skill_dependencies,
    _append_deps_warning,
    MCP_CONFIG_PATTERNS,
)


class TestAppendDepsWarning:
    """Tests for _append_deps_warning helper."""

    def test_mcp_config_patterns_has_all_clients(self):
        """MCP_CONFIG_PATTERNS includes all expected AI clients."""
        expected_clients = [
            "opencode",
            "claude-code",
            "claude-desktop",
            "openclaw",
            "cursor",
            "codex",
            "cline",
            "continue",
        ]
        assert set(MCP_CONFIG_PATTERNS.keys()) == set(expected_clients)

        # Each client should have required fields
        for client, info in MCP_CONFIG_PATTERNS.items():
            assert "files" in info, f"{client} missing 'files'"
            assert "search_key" in info, f"{client} missing 'search_key'"
            assert "format" in info, f"{client} missing 'format'"
            assert isinstance(info["files"], list), f"{client} 'files' should be list"
            assert len(info["files"]) > 0, (
                f"{client} should have at least one config path"
            )

    def test_no_deps_returns_content_unchanged(self):
        """No warning appended when dependencies list is empty."""
        content = "# Test Skill\n\nHello world."
        result = _append_deps_warning("test-skill", [], content)
        assert result == content

    def test_with_deps_prepends_warning(self):
        """Warning is prepended when skill has dependencies."""
        content = "# Test Skill"
        deps = ["https://mcp.sorftime.com"]
        result = _append_deps_warning("test-skill", deps, content)
        assert "[MCP Requirements]" in result
        assert "https://mcp.sorftime.com" in result
        assert "HOW TO CHECK AND CONFIGURE MCP DEPENDENCIES" in result
        assert "Step 1" in result  # New detailed instructions
        assert "opencode" in result.lower()  # Client-specific paths
        assert content in result  # original content still present

    def test_multiple_deps(self):
        """Warning includes all dependencies when multiple are present."""
        content = "# Test Skill"
        deps = ["https://mcp.sorftime.com", "https://mcp.example.com"]
        result = _append_deps_warning("test-skill", deps, content)
        assert "https://mcp.sorftime.com" in result
        assert "https://mcp.example.com" in result

    def test_includes_all_client_paths(self):
        """Warning includes MCP config paths for all supported clients."""
        content = "# Test Skill"
        deps = ["https://mcp.sorftime.com"]
        result = _append_deps_warning("test-skill", deps, content)
        # Check for all major client paths
        assert "claude-code" in result.lower() or "claude_code" in result.lower()
        assert "claude-desktop" in result.lower() or "claude_desktop" in result.lower()
        assert "openclaw" in result.lower()
        assert "cursor" in result.lower()
        assert "codex" in result.lower()
        assert "opencode" in result.lower()
        assert "cline" in result.lower()
        assert "continue" in result.lower()


class TestCallTool:
    """Tests for call_tool function (the decorated MCP call_tool handler)."""

    @pytest.mark.asyncio
    async def test_get_skill_index_with_dependencies(self):
        """get_skill_index appends MCP dependencies warning when skill has deps."""
        skill_name = "time-compare"
        index_data = {"files": [{"name": "SKILL.md", "size": 1024}]}
        skill_with_deps = {
            "id": 1,
            "name": skill_name,
            "dependencies": ["https://mcp.sorftime.com"],
        }

        with patch("app.mcp.server.current_user") as mock_user_ctx:
            mock_user_ctx.get.return_value = {"id": 1}
            with patch(
                "app.services.skill_service.get_skill_index",
                new=AsyncMock(return_value=(index_data, None)),
            ):
                with patch(
                    "app.db.crud.skill.get_by_name",
                    new=AsyncMock(return_value=skill_with_deps),
                ):
                    result = await call_tool(
                        name="get_skill_index",
                        arguments={"skill_name": skill_name},
                    )

        assert len(result) == 1
        assert "[MCP Requirements]" in result[0].text
        assert "https://mcp.sorftime.com" in result[0].text

    @pytest.mark.asyncio
    async def test_get_skill_index_without_dependencies(self):
        """get_skill_index returns raw JSON when skill has no dependencies."""
        skill_name = "hello"
        index_data = {"files": [{"name": "SKILL.md", "size": 256}]}
        skill_without_deps = {
            "id": 1,
            "name": skill_name,
            "dependencies": [],
        }

        with patch("app.mcp.server.current_user") as mock_user_ctx:
            mock_user_ctx.get.return_value = {"id": 1}
            with patch(
                "app.services.skill_service.get_skill_index",
                new=AsyncMock(return_value=(index_data, None)),
            ):
                with patch(
                    "app.db.crud.skill.get_by_name",
                    new=AsyncMock(return_value=skill_without_deps),
                ):
                    result = await call_tool(
                        name="get_skill_index",
                        arguments={"skill_name": skill_name},
                    )

        assert len(result) == 1
        assert "[MCP Requirements]" not in result[0].text
        # Should be plain JSON
        assert '"files"' in result[0].text

    @pytest.mark.asyncio
    async def test_get_skill_file_with_dependencies(self):
        """get_skill_file appends warning when skill has deps."""
        skill_name = "time-compare"
        file_content = "# Time Compare Skill\n\nCompare local and remote time."
        skill_with_deps = {
            "id": 1,
            "name": skill_name,
            "dependencies": ["https://mcp.sorftime.com"],
        }

        # Helper to create async context manager
        class MockAsyncContextManager:
            async def __aenter__(self):
                return MagicMock()

            async def __aexit__(self, *args):
                pass

        with patch("app.mcp.server.current_user") as mock_user_ctx:
            mock_user_ctx.get.return_value = {"id": 1}
            with patch(
                "app.services.skill_service.get_skill_file",
                new=AsyncMock(return_value=(file_content, None)),
            ):
                with patch(
                    "app.db.session.get_db", return_value=MockAsyncContextManager()
                ):
                    with patch(
                        "app.db.crud.skill.get_by_name",
                        new=AsyncMock(return_value=skill_with_deps),
                    ):
                        result = await call_tool(
                            name="get_skill_file",
                            arguments={
                                "skill_name": skill_name,
                                "file_path": "SKILL.md",
                            },
                        )

        assert len(result) == 1
        assert "[MCP Requirements]" in result[0].text
        assert "https://mcp.sorftime.com" in result[0].text
        assert file_content in result[0].text  # original content still there

    @pytest.mark.asyncio
    async def test_get_skill_file_without_dependencies(self):
        """get_skill_file returns raw content when skill has no deps."""
        skill_name = "hello"
        file_content = "# Hello Skill"
        skill_without_deps = {
            "id": 1,
            "name": skill_name,
            "dependencies": [],
        }

        with patch("app.mcp.server.current_user") as mock_user_ctx:
            mock_user_ctx.get.return_value = {"id": 1}
            with patch(
                "app.services.skill_service.get_skill_file",
                new=AsyncMock(return_value=(file_content, None)),
            ):
                with patch(
                    "app.db.crud.skill.get_by_name",
                    new=AsyncMock(return_value=skill_without_deps),
                ):
                    result = await call_tool(
                        name="get_skill_file",
                        arguments={"skill_name": skill_name, "file_path": "SKILL.md"},
                    )

        assert len(result) == 1
        assert "[MCP Requirements]" not in result[0].text
        assert result[0].text == file_content

    @pytest.mark.asyncio
    async def test_legacy_get_skill_name_with_dependencies(self):
        """Legacy get_skill_{name} tool appends warning when skill has deps."""
        skill_name = "time-compare"
        content_json = {"files": [{"name": "SKILL.md", "content": "# Skill"}]}
        skill_with_deps = {
            "id": 1,
            "name": skill_name,
            "dependencies": ["https://mcp.sorftime.com"],
        }

        # Helper to create async context manager
        class MockAsyncContextManager:
            async def __aenter__(self):
                return MagicMock()

            async def __aexit__(self, *args):
                pass

        with patch("app.mcp.server.current_user") as mock_user_ctx:
            mock_user_ctx.get.return_value = {"id": 1}
            with patch(
                "app.services.skill_service.get_skill_content_json",
                new=AsyncMock(return_value=(content_json, None)),
            ):
                with patch(
                    "app.db.session.get_db", return_value=MockAsyncContextManager()
                ):
                    with patch(
                        "app.db.crud.skill.get_by_name",
                        new=AsyncMock(return_value=skill_with_deps),
                    ):
                        result = await call_tool(
                            name=f"get_skill_{skill_name}",
                            arguments={},
                        )

        assert len(result) == 1
        assert "[MCP Requirements]" in result[0].text
        assert "https://mcp.sorftime.com" in result[0].text

    @pytest.mark.asyncio
    async def test_get_skill_index_requires_skill_name(self):
        """get_skill_index returns error when skill_name is missing."""
        with patch("app.mcp.server.current_user") as mock_user_ctx:
            mock_user_ctx.get.return_value = {"id": 1}
            result = await call_tool(name="get_skill_index", arguments={})

        assert len(result) == 1
        assert "Error: skill_name is required" in result[0].text

    @pytest.mark.asyncio
    async def test_get_skill_file_requires_skill_name_and_path(self):
        """get_skill_file returns error when skill_name or file_path is missing."""
        with patch("app.mcp.server.current_user") as mock_user_ctx:
            mock_user_ctx.get.return_value = {"id": 1}

            result = await call_tool(
                name="get_skill_file", arguments={"skill_name": "test"}
            )
            assert "Error: file_path is required" in result[0].text

            result = await call_tool(name="get_skill_file", arguments={})
            assert "Error: skill_name is required" in result[0].text

    @pytest.mark.asyncio
    async def test_get_skill_index_propagates_error(self):
        """get_skill_index returns error from service."""
        with patch("app.mcp.server.current_user") as mock_user_ctx:
            mock_user_ctx.get.return_value = {"id": 1}
            with patch(
                "app.services.skill_service.get_skill_index",
                new=AsyncMock(return_value=(None, "Permission denied")),
            ):
                result = await call_tool(
                    name="get_skill_index",
                    arguments={"skill_name": "forbidden-skill"},
                )

        assert len(result) == 1
        assert "Error: Permission denied" in result[0].text


class TestListTools:
    """Tests for list_tools function."""

    @pytest.mark.asyncio
    async def test_list_tools_includes_global_tools(self):
        """list_tools returns global get_skill_index and get_skill_file tools."""
        mock_skills = []

        # Helper to create async context manager
        class MockAsyncContextManager:
            async def __aenter__(self):
                return MagicMock()

            async def __aexit__(self, *args):
                pass

        with patch("app.mcp.server.current_user") as mock_user_ctx:
            mock_user_ctx.get.return_value = {"id": 1}
            with patch("app.db.session.get_db", return_value=MockAsyncContextManager()):
                with patch(
                    "app.db.crud.user_skill.get_user_skills",
                    new=AsyncMock(return_value=mock_skills),
                ):
                    with patch(
                        "app.db.crud.skill.get_by_ids",
                        new=AsyncMock(return_value=[]),
                    ):
                        result = await list_tools()

        tool_names = [t.name for t in result]
        assert "get_skill_index" in tool_names
        assert "get_skill_file" in tool_names

    @pytest.mark.asyncio
    async def test_list_tools_returns_get_skill_prefix_not_use_skill(self):
        """Per-skill tools use get_skill_ prefix, not use_skill_."""
        mock_skills = [
            {
                "id": 1,
                "name": "time-compare",
                "description": "Compare time",
                "dependencies": [],
            },
        ]

        # Helper to create async context manager
        class MockAsyncContextManager:
            async def __aenter__(self):
                return MagicMock()

            async def __aexit__(self, *args):
                pass

        with patch("app.mcp.server.current_user") as mock_user_ctx:
            mock_user_ctx.get.return_value = {"id": 1}
            with patch("app.db.session.get_db", return_value=MockAsyncContextManager()):
                with patch(
                    "app.db.crud.user_skill.get_user_skills",
                    new=AsyncMock(return_value=mock_skills),
                ):
                    with patch(
                        "app.db.crud.skill.get_by_ids",
                        new=AsyncMock(return_value=mock_skills),
                    ):
                        result = await list_tools()

        tool_names = [t.name for t in result]
        assert "get_skill_time-compare" in tool_names
        # Old prefix should NOT appear
        assert not any(name.startswith("use_skill_") for name in tool_names)
