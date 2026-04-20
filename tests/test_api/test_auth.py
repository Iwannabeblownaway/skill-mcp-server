"""Tests for auth/user_skills API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch


class TestGrantSkill:
    """Tests for POST /api/v1/user_skills endpoint."""

    def test_grant_skill_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully granting a skill to a user."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }
        mock_user = {
            "id": 1,
            "email": "user@example.com",
            "api_key": "user_key",
            "role": "user",
        }
        mock_skill = {
            "id": 1,
            "name": "test_skill",
            "description": "Test",
            "content": "Content",
            "status": "active",
        }

        with patch(
            "app.api.v1.auth.user_crud.get_by_id", new=AsyncMock(return_value=mock_user)
        ):
            with patch(
                "app.api.v1.auth.skill_crud.get_by_id",
                new=AsyncMock(return_value=mock_skill),
            ):
                with patch(
                    "app.api.v1.auth.user_skill_crud.grant",
                    new=AsyncMock(return_value=True),
                ):
                    with patch(
                        "app.api.deps.user_crud.get_by_api_key",
                        new=AsyncMock(return_value=mock_admin),
                    ):
                        response = client.post(
                            "/api/v1/user_skills",
                            json={"user_id": 1, "skill_id": 1},
                            headers=admin_auth_headers,
                        )

        assert response.status_code == 201
        data = response.json()
        assert data["granted"] is True
        assert data["user_id"] == 1
        assert data["skill_id"] == 1

    def test_grant_skill_user_not_found(self, client, admin_auth_headers, mock_get_db):
        """Test granting a skill to a non-existent user."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.auth.user_crud.get_by_id", new=AsyncMock(return_value=None)
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.post(
                    "/api/v1/user_skills",
                    json={"user_id": 999, "skill_id": 1},
                    headers=admin_auth_headers,
                )

        assert response.status_code == 404
        assert "User 999 not found" in response.json()["detail"]

    def test_grant_skill_skill_not_found(self, client, admin_auth_headers, mock_get_db):
        """Test granting a non-existent skill to a user."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }
        mock_user = {
            "id": 1,
            "email": "user@example.com",
            "api_key": "user_key",
            "role": "user",
        }

        with patch(
            "app.api.v1.auth.user_crud.get_by_id", new=AsyncMock(return_value=mock_user)
        ):
            with patch(
                "app.api.v1.auth.skill_crud.get_by_id", new=AsyncMock(return_value=None)
            ):
                with patch(
                    "app.api.deps.user_crud.get_by_api_key",
                    new=AsyncMock(return_value=mock_admin),
                ):
                    response = client.post(
                        "/api/v1/user_skills",
                        json={"user_id": 1, "skill_id": 999},
                        headers=admin_auth_headers,
                    )

        assert response.status_code == 404
        assert "Skill 999 not found" in response.json()["detail"]

    def test_grant_skill_already_exists(self, client, admin_auth_headers, mock_get_db):
        """Test granting a skill that user already has."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }
        mock_user = {
            "id": 1,
            "email": "user@example.com",
            "api_key": "user_key",
            "role": "user",
        }
        mock_skill = {
            "id": 1,
            "name": "test_skill",
            "description": "Test",
            "content": "Content",
            "status": "active",
        }

        with patch(
            "app.api.v1.auth.user_crud.get_by_id", new=AsyncMock(return_value=mock_user)
        ):
            with patch(
                "app.api.v1.auth.skill_crud.get_by_id",
                new=AsyncMock(return_value=mock_skill),
            ):
                with patch(
                    "app.api.v1.auth.user_skill_crud.grant",
                    new=AsyncMock(return_value=False),
                ):
                    with patch(
                        "app.api.deps.user_crud.get_by_api_key",
                        new=AsyncMock(return_value=mock_admin),
                    ):
                        response = client.post(
                            "/api/v1/user_skills",
                            json={"user_id": 1, "skill_id": 1},
                            headers=admin_auth_headers,
                        )

        assert response.status_code == 201
        data = response.json()
        assert data["granted"] is False

    def test_grant_skill_unauthorized(self, client, user_auth_headers):
        """Test granting a skill without admin privileges."""
        mock_user = {
            "id": 1,
            "email": "user@example.com",
            "role": "user",
            "api_key": "user_key",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_user),
        ):
            response = client.post(
                "/api/v1/user_skills",
                json={"user_id": 1, "skill_id": 1},
                headers=user_auth_headers,
            )

        assert response.status_code == 403

    def test_grant_skill_no_auth(self, client):
        """Test granting a skill without authentication."""
        response = client.post(
            "/api/v1/user_skills",
            json={"user_id": 1, "skill_id": 1},
        )

        # FastAPI returns 422 for missing required headers
        assert response.status_code in [401, 422]

    def test_grant_skill_invalid_data(self, client, admin_auth_headers):
        """Test granting a skill with invalid data."""
        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_admin),
        ):
            # Missing skill_id
            response = client.post(
                "/api/v1/user_skills",
                json={"user_id": 1},
                headers=admin_auth_headers,
            )

        assert response.status_code == 422  # Validation error


class TestRevokeSkill:
    """Tests for DELETE /api/v1/user_skills endpoint."""

    def test_revoke_skill_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully revoking a skill from a user."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.auth.user_skill_crud.revoke", new=AsyncMock(return_value=True)
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.delete(
                    "/api/v1/user_skills?user_id=1&skill_id=1",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 204

    def test_revoke_skill_not_found(self, client, admin_auth_headers, mock_get_db):
        """Test revoking a skill that user doesn't have."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.auth.user_skill_crud.revoke", new=AsyncMock(return_value=False)
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.delete(
                    "/api/v1/user_skills?user_id=1&skill_id=999",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_revoke_skill_unauthorized(self, client, user_auth_headers):
        """Test revoking a skill without admin privileges."""
        mock_user = {
            "id": 1,
            "email": "user@example.com",
            "role": "user",
            "api_key": "user_key",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_user),
        ):
            response = client.delete(
                "/api/v1/user_skills?user_id=1&skill_id=1",
                headers=user_auth_headers,
            )

        assert response.status_code == 403

    def test_revoke_skill_no_auth(self, client):
        """Test revoking a skill without authentication."""
        response = client.delete("/api/v1/user_skills?user_id=1&skill_id=1")

        # FastAPI returns 422 for missing required headers
        assert response.status_code in [401, 422]

    def test_revoke_skill_missing_params(self, client, admin_auth_headers):
        """Test revoking a skill without required parameters."""
        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_admin),
        ):
            # Missing skill_id
            response = client.delete(
                "/api/v1/user_skills?user_id=1",
                headers=admin_auth_headers,
            )

        assert response.status_code == 422  # Validation error


class TestAuthDependencies:
    """Tests for authentication dependencies."""

    def test_get_current_user_valid_key(self, client, mock_get_db):
        """Test authentication with valid API key."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 1,
            "email": "user@example.com",
            "api_key": "valid_key",
            "role": "user",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_user),
        ):
            # Access an endpoint that requires authentication
            response = client.get(
                "/api/v1/users",
                headers={"X-API-Key": "valid_key"},
            )

        # Should not get 401, endpoint behavior depends on role
        assert response.status_code != 401

    def test_get_current_user_invalid_key(self, client):
        """Test authentication with invalid API key."""
        with patch(
            "app.api.deps.user_crud.get_by_api_key", new=AsyncMock(return_value=None)
        ):
            response = client.get(
                "/api/v1/users",
                headers={"X-API-Key": "invalid_key"},
            )

        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_get_current_user_missing_key(self, client):
        """Test authentication without API key header."""
        response = client.get("/api/v1/users")

        # FastAPI returns 422 for missing required headers
        assert response.status_code in [401, 422]

    def test_verify_admin_api_key_valid_admin(self, client, mock_get_db):
        """Test admin verification with valid admin key."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "api_key": "admin_key",
            "role": "admin",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_admin),
        ):
            response = client.post(
                "/api/v1/skills",
                json={"name": "test", "description": "Test", "content": "Content"},
                headers={"X-API-Key": "admin_key"},
            )

        # Should not get 403 (forbidden), might get other errors
        assert response.status_code != 403

    def test_verify_admin_api_key_regular_user(self, client, mock_get_db):
        """Test admin verification with regular user key."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 1,
            "email": "user@example.com",
            "api_key": "user_key",
            "role": "user",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_user),
        ):
            response = client.post(
                "/api/v1/skills",
                json={"name": "test", "description": "Test", "content": "Content"},
                headers={"X-API-Key": "user_key"},
            )

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]
