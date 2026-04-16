"""Tests for users API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch


class TestCreateUser:
    """Tests for POST /api/v1/users endpoint."""

    def test_create_user_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully creating a new user."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "external_id": "admin_001",
            "username": "Admin",
            "role": "admin",
            "api_key": "admin_key",
        }

        new_user = {
            "id": 3,
            "external_id": "user_003",
            "username": "NewUser",
            "api_key": "generated_api_key_xyz123",
            "role": "user",
        }

        with patch(
            "app.api.v1.users.user_crud.create", new=AsyncMock(return_value=new_user)
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.post(
                    "/api/v1/users",
                    json={
                        "user_id": "user_003",
                        "username": "NewUser",
                        "role": "user",
                    },
                    headers=admin_auth_headers,
                )

        assert response.status_code == 201
        assert response.json()["user_id"] == "user_003"
        assert response.json()["username"] == "NewUser"
        assert response.json()["api_key"] == "generated_api_key_xyz123"
        assert response.json()["role"] == "user"

    def test_create_user_admin_role(self, client, admin_auth_headers, mock_get_db):
        """Test creating a user with admin role."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "external_id": "admin_001",
            "username": "Admin",
            "role": "admin",
            "api_key": "admin_key",
        }

        new_admin = {
            "id": 4,
            "external_id": "newadmin",
            "username": "NewAdmin",
            "api_key": "admin_api_key_xyz123",
            "role": "admin",
        }

        with patch(
            "app.api.v1.users.user_crud.create", new=AsyncMock(return_value=new_admin)
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.post(
                    "/api/v1/users",
                    json={
                        "user_id": "newadmin",
                        "username": "NewAdmin",
                        "role": "admin",
                    },
                    headers=admin_auth_headers,
                )

        assert response.status_code == 201
        assert response.json()["role"] == "admin"

    def test_create_user_default_role(self, client, admin_auth_headers, mock_get_db):
        """Test creating a user with default role."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "external_id": "admin_001",
            "username": "Admin",
            "role": "admin",
            "api_key": "admin_key",
        }

        new_user = {
            "id": 5,
            "external_id": "default_user",
            "username": "DefaultUser",
            "api_key": "api_key_default",
            "role": "user",
        }

        with patch(
            "app.api.v1.users.user_crud.create", new=AsyncMock(return_value=new_user)
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.post(
                    "/api/v1/users",
                    json={"user_id": "default_user", "username": "DefaultUser"},
                    headers=admin_auth_headers,
                )

        assert response.status_code == 201
        assert response.json()["role"] == "user"

    def test_create_user_unauthorized(self, client, user_auth_headers):
        """Test creating a user without admin privileges."""
        mock_user = {
            "id": 1,
            "external_id": "user_001",
            "username": "User",
            "role": "user",
            "api_key": "user_key",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_user),
        ):
            response = client.post(
                "/api/v1/users",
                json={"user_id": "newuser", "username": "NewUser"},
                headers=user_auth_headers,
            )

        assert response.status_code == 403

    def test_create_user_no_auth(self, client):
        """Test creating a user without authentication."""
        response = client.post(
            "/api/v1/users",
            json={"user_id": "newuser", "username": "NewUser"},
        )

        # FastAPI returns 422 for missing required headers
        assert response.status_code in [401, 422]

    def test_create_user_invalid_data(self, client, admin_auth_headers, mock_get_db):
        """Test creating a user with invalid/missing data."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "external_id": "admin_001",
            "username": "Admin",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_admin),
        ):
            # Missing required user_id field
            response = client.post(
                "/api/v1/users",
                json={"username": "SomeUser"},  # Missing user_id
                headers=admin_auth_headers,
            )

        assert response.status_code == 422  # Validation error


class TestListUsers:
    """Tests for GET /api/v1/users endpoint."""

    def test_list_users_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully listing users."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "external_id": "admin_001",
            "username": "Admin",
            "role": "admin",
            "api_key": "admin_key",
        }

        users_list = [
            {
                "id": 1,
                "external_id": "user_001",
                "username": "User1",
                "api_key": "key1",
                "role": "user",
                "created_at": "2024-01-01",
            },
            {
                "id": 2,
                "external_id": "admin_001",
                "username": "Admin",
                "api_key": "key2",
                "role": "admin",
                "created_at": "2024-01-01",
            },
        ]

        with patch(
            "app.api.v1.users.user_crud.list_users",
            new=AsyncMock(return_value=users_list),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/users",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_users_pagination(self, client, admin_auth_headers, mock_get_db):
        """Test listing users with pagination."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "external_id": "admin_001",
            "username": "Admin",
            "role": "admin",
            "api_key": "admin_key",
        }

        users_list = [
            {
                "id": 3,
                "external_id": "user_003",
                "username": "User3",
                "api_key": "key3",
                "role": "user",
                "created_at": "2024-01-01",
            },
        ]

        with patch(
            "app.api.v1.users.user_crud.list_users",
            new=AsyncMock(return_value=users_list),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/users?page=2&page_size=10",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    def test_list_users_empty(self, client, admin_auth_headers, mock_get_db):
        """Test listing users when none exist."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "external_id": "admin_001",
            "username": "Admin",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.users.user_crud.list_users", new=AsyncMock(return_value=[])
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/users",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["users"] == []
        assert data["total"] == 0

    def test_list_users_unauthorized(self, client, user_auth_headers):
        """Test listing users without admin privileges."""
        mock_user = {
            "id": 1,
            "external_id": "user_001",
            "username": "User",
            "role": "user",
            "api_key": "user_key",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_user),
        ):
            response = client.get(
                "/api/v1/users",
                headers=user_auth_headers,
            )

        assert response.status_code == 403

    def test_list_users_invalid_page(self, client, admin_auth_headers):
        """Test listing users with invalid page number."""
        mock_admin = {
            "id": 2,
            "external_id": "admin_001",
            "username": "Admin",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_admin),
        ):
            response = client.get(
                "/api/v1/users?page=0",
                headers=admin_auth_headers,
            )

        assert response.status_code == 422  # Validation error

    def test_list_users_invalid_page_size(self, client, admin_auth_headers):
        """Test listing users with invalid page size."""
        mock_admin = {
            "id": 2,
            "external_id": "admin_001",
            "username": "Admin",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_admin),
        ):
            # Page size too large
            response = client.get(
                "/api/v1/users?page_size=200",
                headers=admin_auth_headers,
            )

        assert response.status_code == 422  # Validation error
