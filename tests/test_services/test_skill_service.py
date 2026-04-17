"""Tests for skill_service module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import skill_service


class TestGetUserSkills:
    """Tests for get_user_skills function."""

    @pytest.mark.asyncio
    async def test_get_user_skills_success(self, mock_get_db):
        """Test successfully retrieving user skills."""
        conn, cursor = mock_get_db

        # Mock user_skill_crud.get_user_skills to return skills
        mock_skills = [
            {"name": "skill_1", "description": "First skill", "content": "Content 1"},
            {"name": "skill_2", "description": "Second skill", "content": "Content 2"},
        ]

        with patch(
            "app.services.skill_service.user_skill_crud.get_user_skills",
            new=AsyncMock(return_value=mock_skills),
        ):
            result = await skill_service.get_user_skills(user_id=1)

        assert len(result) == 2
        assert result[0]["name"] == "skill_1"
        assert result[0]["description"] == "First skill"
        assert "content" not in result[0]  # Content should not be included

    @pytest.mark.asyncio
    async def test_get_user_skills_empty(self, mock_get_db):
        """Test retrieving skills when user has no skills."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.user_skill_crud.get_user_skills",
            new=AsyncMock(return_value=[]),
        ):
            result = await skill_service.get_user_skills(user_id=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_skills_single(self, mock_get_db):
        """Test retrieving single skill for user."""
        conn, cursor = mock_get_db

        mock_skills = [
            {"name": "only_skill", "description": "Only skill", "content": "Content"},
        ]

        with patch(
            "app.services.skill_service.user_skill_crud.get_user_skills",
            new=AsyncMock(return_value=mock_skills),
        ):
            result = await skill_service.get_user_skills(user_id=1)

        assert len(result) == 1
        assert result[0]["name"] == "only_skill"


class TestCheckPermission:
    """Tests for check_permission function."""

    @pytest.mark.asyncio
    async def test_check_permission_granted(self, mock_get_db):
        """Test permission check when user has skill access."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.user_skill_crud.has_skill",
            new=AsyncMock(return_value=True),
        ):
            result = await skill_service.check_permission(
                user_id=1, skill_name="test_skill"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_denied(self, mock_get_db):
        """Test permission check when user doesn't have skill access."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.user_skill_crud.has_skill",
            new=AsyncMock(return_value=False),
        ):
            result = await skill_service.check_permission(
                user_id=1, skill_name="test_skill"
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_nonexistent_skill(self, mock_get_db):
        """Test permission check for non-existent skill."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.user_skill_crud.has_skill",
            new=AsyncMock(return_value=False),
        ):
            result = await skill_service.check_permission(
                user_id=1, skill_name="nonexistent"
            )

        assert result is False


class TestGetSkillContent:
    """Tests for get_skill_content function."""

    @pytest.mark.asyncio
    async def test_get_skill_content_success(self, mock_get_db, sample_skill):
        """Test successfully retrieving skill content with permission."""
        conn, cursor = mock_get_db

        expected_content = "# Test Skill\n\nThis is a test skill content."

        with patch(
            "app.services.skill_service.skill_crud.get_by_name",
            new=AsyncMock(return_value=sample_skill),
        ):
            with patch(
                "app.services.skill_service.user_skill_crud.has_skill",
                new=AsyncMock(return_value=True),
            ):
                with patch(
                    "app.services.skill_service.skill_crud.get_content_json",
                    new=AsyncMock(return_value=None),
                ):
                    with patch(
                        "app.services.skill_service.skill_crud.load_skill_content",
                        new=MagicMock(return_value=expected_content),
                    ):
                        content, error = await skill_service.get_skill_content(
                            user_id=1, skill_name="test_skill"
                        )

        assert error is None
        assert content == expected_content

    @pytest.mark.asyncio
    async def test_get_skill_content_not_found(self, mock_get_db):
        """Test retrieving content for non-existent skill."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.skill_crud.get_by_name",
            new=AsyncMock(return_value=None),
        ):
            content, error = await skill_service.get_skill_content(
                user_id=1, skill_name="nonexistent"
            )

        assert content is None
        assert error == "Skill not found"

    @pytest.mark.asyncio
    async def test_get_skill_content_permission_denied(self, mock_get_db, sample_skill):
        """Test retrieving content without permission."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.skill_crud.get_by_name",
            new=AsyncMock(return_value=sample_skill),
        ):
            with patch(
                "app.services.skill_service.user_skill_crud.has_skill",
                new=AsyncMock(return_value=False),
            ):
                content, error = await skill_service.get_skill_content(
                    user_id=1, skill_name="test_skill"
                )

        assert content is None
        assert error == "Permission denied"

    @pytest.mark.asyncio
    async def test_get_skill_content_empty_content(self, mock_get_db):
        """Test retrieving skill with empty content."""
        conn, cursor = mock_get_db
        skill_with_empty_content = {
            "id": 1,
            "name": "empty_skill",
            "description": "Empty skill",
            "path": "empty_skill",
            "version": "1.0",
        }

        with patch(
            "app.services.skill_service.skill_crud.get_by_name",
            new=AsyncMock(return_value=skill_with_empty_content),
        ):
            with patch(
                "app.services.skill_service.user_skill_crud.has_skill",
                new=AsyncMock(return_value=True),
            ):
                with patch(
                    "app.services.skill_service.skill_crud.get_content_json",
                    new=AsyncMock(return_value=None),
                ):
                    with patch(
                        "app.services.skill_service.skill_crud.load_skill_content",
                        new=MagicMock(return_value=""),
                    ):
                        content, error = await skill_service.get_skill_content(
                            user_id=1, skill_name="empty_skill"
                        )

        assert error is None
        assert content == ""


class TestLogCall:
    """Tests for log_call function."""

    @pytest.mark.asyncio
    async def test_log_call_success(self, mock_get_db, sample_skill):
        """Test successfully logging a successful skill call."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.skill_crud.get_by_name",
            new=AsyncMock(return_value=sample_skill),
        ):
            with patch(
                "app.services.skill_service.call_log_crud.create_log",
                new=AsyncMock(return_value=1),
            ) as mock_create_log:
                await skill_service.log_call(
                    user_id=1,
                    skill_name="test_skill",
                    status="success",
                    error_msg="",
                    duration_ms=150,
                )

                mock_create_log.assert_called_once_with(
                    conn,
                    user_id=1,
                    skill_id=sample_skill["id"],
                    status="success",
                    error_message=None,
                    duration_ms=150,
                )

    @pytest.mark.asyncio
    async def test_log_call_failure(self, mock_get_db, sample_skill):
        """Test logging a failed skill call."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.skill_crud.get_by_name",
            new=AsyncMock(return_value=sample_skill),
        ):
            with patch(
                "app.services.skill_service.call_log_crud.create_log",
                new=AsyncMock(return_value=2),
            ) as mock_create_log:
                await skill_service.log_call(
                    user_id=1,
                    skill_name="test_skill",
                    status="failure",
                    error_msg="Something went wrong",
                    duration_ms=50,
                )

                mock_create_log.assert_called_once_with(
                    conn,
                    user_id=1,
                    skill_id=sample_skill["id"],
                    status="failure",
                    error_message="Something went wrong",
                    duration_ms=50,
                )

    @pytest.mark.asyncio
    async def test_log_call_denied(self, mock_get_db, sample_skill):
        """Test logging a denied skill call."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.skill_crud.get_by_name",
            new=AsyncMock(return_value=sample_skill),
        ):
            with patch(
                "app.services.skill_service.call_log_crud.create_log",
                new=AsyncMock(return_value=3),
            ) as mock_create_log:
                await skill_service.log_call(
                    user_id=1,
                    skill_name="test_skill",
                    status="denied",
                    error_msg="Permission denied",
                    duration_ms=10,
                )

                mock_create_log.assert_called_once_with(
                    conn,
                    user_id=1,
                    skill_id=sample_skill["id"],
                    status="denied",
                    error_message="Permission denied",
                    duration_ms=10,
                )

    @pytest.mark.asyncio
    async def test_log_call_skill_not_found(self, mock_get_db):
        """Test logging when skill doesn't exist."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.skill_crud.get_by_name",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "app.services.skill_service.call_log_crud.create_log", new=AsyncMock()
            ) as mock_create_log:
                await skill_service.log_call(
                    user_id=1,
                    skill_name="nonexistent",
                    status="success",
                    error_msg="",
                    duration_ms=100,
                )

                # create_log should not be called if skill not found
                mock_create_log.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_call_zero_duration(self, mock_get_db, sample_skill):
        """Test logging with zero duration."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.skill_service.skill_crud.get_by_name",
            new=AsyncMock(return_value=sample_skill),
        ):
            with patch(
                "app.services.skill_service.call_log_crud.create_log",
                new=AsyncMock(return_value=4),
            ) as mock_create_log:
                await skill_service.log_call(
                    user_id=1,
                    skill_name="test_skill",
                    status="success",
                    error_msg="",
                    duration_ms=0,
                )

                mock_create_log.assert_called_once_with(
                    conn,
                    user_id=1,
                    skill_id=sample_skill["id"],
                    status="success",
                    error_message=None,
                    duration_ms=0,
                )
