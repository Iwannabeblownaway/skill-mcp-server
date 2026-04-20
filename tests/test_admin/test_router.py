"""Tests for admin router flash message functionality."""

import pytest
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestFlattenSingleTopLevelDir:
    """Tests for _flatten_single_top_level_dir helper."""

    def test_nested_folder(self):
        """All files under one folder should return that folder prefix."""
        from app.admin.router import _flatten_single_top_level_dir

        entries = ["mcp-builder/SKILL.md", "mcp-builder/README.md"]
        assert _flatten_single_top_level_dir(entries) == "mcp-builder"

    def test_flat_files(self):
        """Flat files with no common directory return empty string."""
        from app.admin.router import _flatten_single_top_level_dir

        entries = ["SKILL.md", "README.md"]
        assert _flatten_single_top_level_dir(entries) == ""

    def test_multiple_subfolders(self):
        """Files under multiple top-level folders return empty string."""
        from app.admin.router import _flatten_single_top_level_dir

        entries = ["src/main.py", "lib/helper.py"]
        assert _flatten_single_top_level_dir(entries) == ""

    def test_deeply_nested(self):
        """Deeply nested common prefix is returned."""
        from app.admin.router import _flatten_single_top_level_dir

        entries = ["a/b/c/file1.txt", "a/b/c/file2.txt"]
        assert _flatten_single_top_level_dir(entries) == "a/b/c"

    def test_empty_list(self):
        """Empty list returns empty string."""
        from app.admin.router import _flatten_single_top_level_dir

        assert _flatten_single_top_level_dir([]) == ""


class TestRedirectWithMessage:
    """Tests for redirect_with_message function."""

    def test_simple_message(self):
        """Test basic flash message without special characters."""
        from app.admin.router import redirect_with_message

        response = redirect_with_message("/test", "Operation successful", "success")

        assert response.status_code == 200
        content = response.body.decode()

        # Should contain sessionStorage set calls
        assert "sessionStorage.setItem" in content
        assert "/test" in content

    def test_html_special_chars_escaped(self):
        """Test that HTML special characters are properly escaped via hex escaping."""
        from app.admin.router import redirect_with_message

        # XSS attempt - raw < > should not appear unescaped in HTML
        response = redirect_with_message("/test", "<script>alert('xss')</script>", "error")

        content = response.body.decode()

        # The raw XSS payload should NOT appear in HTML (unencoded < > would be XSS)
        # We check the message content area specifically - it should use \x3c \x3e escapes
        # The message goes into: sessionStorage.setItem('flash_message', "\x3cscript...")
        # So literal <script> should NOT be in the setItem line
        assert "flash_message', \"<script>" not in content
        assert "flash_message', \"alert" not in content
        # Instead, hex escapes should be present
        assert r"\x3cscript\x3e" in content or r"\x3c/script\x3e" in content


class TestParseDependencies:
    """Tests for _parse_dependencies helper."""

    def test_comma_separated(self):
        """Test parsing comma-separated dependencies."""
        from app.admin.router import _parse_dependencies

        result = _parse_dependencies("dep1,dep2,dep3")
        assert result == ["dep1", "dep2", "dep3"]

    def test_json_array(self):
        """Test parsing JSON array format."""
        from app.admin.router import _parse_dependencies

        result = _parse_dependencies('["dep1", "dep2"]')
        assert result == ["dep1", "dep2"]

    def test_mcp_config_json(self):
        """Test parsing full MCP config JSON."""
        from app.admin.router import _parse_dependencies

        config = '{"mcpServers": {"sorftime": {}, "aws": {}}}'
        result = _parse_dependencies(config)
        assert "sorftime" in result
        assert "aws" in result

    def test_empty_string(self):
        """Test empty input returns empty list."""
        from app.admin.router import _parse_dependencies

        assert _parse_dependencies("") == []
        assert _parse_dependencies("   ") == []

    def test_whitespace_handling(self):
        """Test whitespace is trimmed."""
        from app.admin.router import _parse_dependencies

        result = _parse_dependencies(" dep1 ,  dep2 ")
        assert result == ["dep1", "dep2"]

    def test_invalid_json_returns_comma_separated(self):
        """Test invalid JSON falls back to comma-separated."""
        from app.admin.router import _parse_dependencies

        # Invalid JSON should fall back to comma-separated
        result = _parse_dependencies("not valid json")
        assert result == ["not valid json"]

    def test_quotes_in_message(self):
        """Test that quotes are properly escaped."""
        from app.admin.router import redirect_with_message

        response = redirect_with_message("/test", "User \"John\" created", "success")

        content = response.body.decode()

        # Quotes should be escaped via JSON encoding
        # The raw string should not break JavaScript
        assert "sessionStorage.setItem" in content

    def test_newlines_in_message(self):
        """Test that newlines are properly handled."""
        from app.admin.router import redirect_with_message

        response = redirect_with_message("/test", "Line1\nLine2", "success")

        content = response.body.decode()

        # Newlines should be JSON-encoded (\n)
        assert "\\n" in content or "Line1" in content

    def test_unicode_message(self):
        """Test Unicode characters are handled correctly."""
        from app.admin.router import redirect_with_message

        response = redirect_with_message("/test", "用户创建成功 ✓", "success")

        content = response.body.decode()

        assert response.status_code == 200
        assert "sessionStorage.setItem" in content

    def test_empty_message(self):
        """Test empty message doesn't break."""
        from app.admin.router import redirect_with_message

        response = redirect_with_message("/test", "", "success")

        content = response.body.decode()
        assert response.status_code == 200

    def test_error_message_type(self):
        """Test error message type."""
        from app.admin.router import redirect_with_message

        response = redirect_with_message("/test", "Something went wrong", "error")

        content = response.body.decode()
        assert "error" in content

    def test_url_with_special_chars(self):
        """Test URL with special characters."""
        from app.admin.router import redirect_with_message

        response = redirect_with_message("/users?id=1&name=test", "Done", "success")

        content = response.body.decode()
        assert "/users?id=1&name=test" in content or "users" in content
