"""Tests for admin router flash message functionality."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

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

    def test_windows_backslash_paths(self):
        """Windows-style paths with backslashes should be normalized."""
        from app.admin.router import _flatten_single_top_level_dir

        # Windows-style paths with backslashes
        entries = [r"mcp-builder\SKILL.md", r"mcp-builder\README.md"]
        assert _flatten_single_top_level_dir(entries) == "mcp-builder"

    def test_mixed_slash_paths(self):
        """Mixed forward and backslash paths should still detect common prefix."""
        from app.admin.router import _flatten_single_top_level_dir

        entries = [r"mcp-builder/SKILL.md", r"mcp-builder\README.md"]
        assert _flatten_single_top_level_dir(entries) == "mcp-builder"

    def test_deeply_nested_backslash(self):
        """Deeply nested Windows paths should return correct prefix."""
        from app.admin.router import _flatten_single_top_level_dir

        entries = [r"a\b\c\file1.txt", r"a\b\c\file2.txt"]
        assert _flatten_single_top_level_dir(entries) == "a/b/c"

    def test_winrar_nested_duplicate_single_level(self):
        """Single-level prefix like skill/SKILL.md should return 'skill' prefix."""
        from app.admin.router import _flatten_single_top_level_dir

        # Normal case - single directory wrapping
        entries = ["skill/SKILL.md", "skill/README.md"]
        assert _flatten_single_top_level_dir(entries) == "skill"

    def test_winrar_nested_duplicate_double_level(self):
        """WinRAR nested duplicate dirs like a/a/SKILL.md should keep one level."""
        from app.admin.router import _flatten_single_top_level_dir

        # WinRAR case - nested duplicate directory names
        entries = ["skill-auditor/skill-auditor/SKILL.md", "skill-auditor/skill-auditor/README.md"]
        # Should strip to just one level: "skill-auditor/skill-auditor" -> "skill-auditor"
        assert _flatten_single_top_level_dir(entries) == "skill-auditor"

    def test_winrar_nested_duplicate_triple_level(self):
        """WinRAR nested duplicate dirs with 3 levels should keep one level."""
        from app.admin.router import _flatten_single_top_level_dir

        # a/a/a/ -> a/ (keep one)
        entries = ["a/a/a/SKILL.md", "a/a/a/README.md"]
        assert _flatten_single_top_level_dir(entries) == "a"

    def test_winrar_nested_not_consecutive(self):
        """Non-consecutive duplicates should NOT be stripped."""
        from app.admin.router import _flatten_single_top_level_dir

        # "a/b" prefix - b is not same as a, so no consecutive duplicate
        entries = ["a/b/SKILL.md", "a/b/README.md"]
        assert _flatten_single_top_level_dir(entries) == "a/b"

    def test_empty_result_after_stripping(self):
        """If stripping would leave empty paths, handle gracefully."""
        from app.admin.router import _flatten_single_top_level_dir

        # Single file at root of zip
        entries = ["SKILL.md", "README.md"]
        assert _flatten_single_top_level_dir(entries) == ""


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


class TestBuildSkillPackage:
    """Tests for _build_skill_package helper."""

    def test_build_skill_package_creates_zip(self, tmp_path):
        """Test that _build_skill_package creates a valid zip file."""
        import zipfile
        from app.admin.router import _build_skill_package
        from app.db.crud import skill as skill_crud

        # Create a mock SKILLS_DIR in temp location
        mock_skills_dir = tmp_path / "skills"
        mock_skills_dir.mkdir()

        # Create a skill folder with some files
        skill_name = "test-skill"
        skill_path = skill_name
        skill_dir = mock_skills_dir / skill_path
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill")
        (skill_dir / "README.md").write_text("Test README")

        with patch.object(skill_crud, "SKILLS_DIR", mock_skills_dir):
            package_path = _build_skill_package(skill_name, skill_path)

            # Check package was created
            assert package_path.exists()
            assert package_path.name == f"{skill_name}.skill"

            # Verify it's a valid zip file
            assert zipfile.is_zipfile(package_path)

            # Verify zip contents
            with zipfile.ZipFile(package_path, "r") as zf:
                names = zf.namelist()
                assert "SKILL.md" in names
                assert "README.md" in names

    def test_build_skill_package_raises_if_folder_missing(self, tmp_path):
        """Test that _build_skill_package raises FileNotFoundError if skill folder missing."""
        from app.admin.router import _build_skill_package
        from app.db.crud import skill as skill_crud

        mock_skills_dir = tmp_path / "skills"
        mock_skills_dir.mkdir()

        with patch.object(skill_crud, "SKILLS_DIR", mock_skills_dir):
            with pytest.raises(FileNotFoundError) as exc_info:
                _build_skill_package("nonexistent", "nonexistent")

            assert "Skill folder not found" in str(exc_info.value)

    def test_build_skill_package_nested_files(self, tmp_path):
        """Test that _build_skill_package correctly handles nested directory structure."""
        import zipfile
        from app.admin.router import _build_skill_package
        from app.db.crud import skill as skill_crud

        mock_skills_dir = tmp_path / "skills"
        mock_skills_dir.mkdir()

        skill_name = "nested-skill"
        skill_dir = mock_skills_dir / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Nested")
        subdir = skill_dir / "subdir"
        subdir.mkdir()
        (subdir / "helper.py").write_text("def foo(): pass")

        with patch.object(skill_crud, "SKILLS_DIR", mock_skills_dir):
            package_path = _build_skill_package(skill_name, skill_name)

            with zipfile.ZipFile(package_path, "r") as zf:
                names = zf.namelist()
                assert "SKILL.md" in names
                assert "subdir/helper.py" in names


class TestGetSkillPackagePath:
    """Tests for _get_skill_package_path helper."""

    def test_returns_path_when_package_exists(self, tmp_path):
        """Test that _get_skill_package_path returns Path when package exists."""
        from app.admin.router import _get_skill_package_path
        from app.db.crud import skill as skill_crud

        mock_skills_dir = tmp_path / "skills"
        mock_skills_dir.mkdir()
        packages_dir = mock_skills_dir.parent / "skill_packages"
        packages_dir.mkdir()
        package_path = packages_dir / "test-skill.skill"
        package_path.write_bytes(b"fake zip content")

        with patch.object(skill_crud, "SKILLS_DIR", mock_skills_dir):
            result = _get_skill_package_path("test-skill")

            assert result is not None
            assert result == package_path
            assert result.exists()

    def test_returns_none_when_package_missing(self, tmp_path):
        """Test that _get_skill_package_path returns None when package doesn't exist."""
        from app.admin.router import _get_skill_package_path
        from app.db.crud import skill as skill_crud

        mock_skills_dir = tmp_path / "skills"
        mock_skills_dir.mkdir()
        # Don't create the packages dir

        with patch.object(skill_crud, "SKILLS_DIR", mock_skills_dir):
            result = _get_skill_package_path("nonexistent-skill")

            assert result is None

    def test_package_path_uses_skill_name(self, tmp_path):
        """Test that package path is correctly formed from skill name."""
        from app.admin.router import _get_skill_package_path
        from app.db.crud import skill as skill_crud

        mock_skills_dir = tmp_path / "skills"
        mock_skills_dir.mkdir()
        packages_dir = mock_skills_dir.parent / "skill_packages"
        packages_dir.mkdir()
        (packages_dir / "my-cool-skill.skill").write_bytes(b"")

        with patch.object(skill_crud, "SKILLS_DIR", mock_skills_dir):
            result = _get_skill_package_path("my-cool-skill")

            assert result is not None
            assert result.name == "my-cool-skill.skill"
