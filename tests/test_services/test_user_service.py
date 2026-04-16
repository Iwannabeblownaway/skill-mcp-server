"""Tests for user_service module."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services import user_service


class TestVerifyApiKey:
    """Tests for verify_api_key function."""

    @pytest.mark.asyncio
    async def test_verify_api_key_success(self, mock_get_db, sample_user):
        """Test verifying a valid API key."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.user_service.user_crud.get_by_api_key",
            new=AsyncMock(return_value=sample_user),
        ):
            result = await user_service.verify_api_key("test_api_key_12345")

        assert result is not None
        assert result["id"] == sample_user["id"]
        assert result["external_id"] == sample_user["external_id"]
        assert result["role"] == sample_user["role"]

    @pytest.mark.asyncio
    async def test_verify_api_key_invalid(self, mock_get_db):
        """Test verifying an invalid API key."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.user_service.user_crud.get_by_api_key",
            new=AsyncMock(return_value=None),
        ):
            result = await user_service.verify_api_key("invalid_api_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_api_key_empty(self, mock_get_db):
        """Test verifying an empty API key."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.user_service.user_crud.get_by_api_key",
            new=AsyncMock(return_value=None),
        ):
            result = await user_service.verify_api_key("")

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_api_key_admin(self, mock_get_db, sample_admin):
        """Test verifying an admin API key."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.user_service.user_crud.get_by_api_key",
            new=AsyncMock(return_value=sample_admin),
        ):
            result = await user_service.verify_api_key("admin_api_key_12345")

        assert result is not None
        assert result["role"] == "admin"


class TestCreateUser:
    """Tests for create_user function."""

    @pytest.mark.asyncio
    async def test_create_user_default_role(self, mock_get_db):
        """Test creating a user with default role."""
        conn, cursor = mock_get_db

        created_user = {
            "id": 1,
            "user_id": "newuser",
            "username": "NewUser",
            "api_key": "generated_api_key_123",
            "role": "user",
        }

        with patch(
            "app.services.user_service.user_crud.create",
            new=AsyncMock(return_value=created_user),
        ):
            result = await user_service.create_user("newuser", "NewUser")

        assert result["id"] == 1
        assert result["user_id"] == "newuser"
        assert result["role"] == "user"
        assert "api_key" in result

    @pytest.mark.asyncio
    async def test_create_user_admin_role(self, mock_get_db):
        """Test creating a user with admin role."""
        conn, cursor = mock_get_db

        created_user = {
            "id": 2,
            "user_id": "newadmin",
            "username": "NewAdmin",
            "api_key": "admin_api_key_456",
            "role": "admin",
        }

        with patch(
            "app.services.user_service.user_crud.create",
            new=AsyncMock(return_value=created_user),
        ):
            result = await user_service.create_user(
                "newadmin", "NewAdmin", role="admin"
            )

        assert result["role"] == "admin"

    @pytest.mark.asyncio
    async def test_create_user_returns_api_key(self, mock_get_db):
        """Test that created user includes API key."""
        conn, cursor = mock_get_db

        created_user = {
            "id": 3,
            "user_id": "testuser",
            "username": "TestUser",
            "api_key": "unique_api_key_xyz",
            "role": "user",
        }

        with patch(
            "app.services.user_service.user_crud.create",
            new=AsyncMock(return_value=created_user),
        ):
            result = await user_service.create_user("testuser", "TestUser")

        assert result["api_key"] == "unique_api_key_xyz"


class TestGetUserById:
    """Tests for get_user_by_id function."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, mock_get_db, sample_user):
        """Test getting user by valid ID."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.user_service.user_crud.get_by_id",
            new=AsyncMock(return_value=sample_user),
        ):
            result = await user_service.get_user_by_id(1)

        assert result is not None
        assert result["id"] == 1
        assert result["external_id"] == sample_user["external_id"]

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, mock_get_db):
        """Test getting user by non-existent ID."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.user_service.user_crud.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            result = await user_service.get_user_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_zero(self, mock_get_db):
        """Test getting user by ID 0."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.user_service.user_crud.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            result = await user_service.get_user_by_id(0)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_negative(self, mock_get_db):
        """Test getting user by negative ID."""
        conn, cursor = mock_get_db

        with patch(
            "app.services.user_service.user_crud.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            result = await user_service.get_user_by_id(-1)

        assert result is None
