"""Tests for skills API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch


class TestCreateSkill:
    """Tests for POST /api/v1/skills endpoint."""

    def test_create_skill_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully creating a new skill."""
        conn, cursor = mock_get_db

        skill_data = {
            "name": "new_skill",
            "description": "A new test skill",
            "content": "# New Skill\n\nContent here.",
            "version": "1.0",
        }

        mock_user = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name", new=AsyncMock(return_value=None)
        ):
            with patch(
                "app.api.v1.skills.skill_crud.create",
                new=AsyncMock(
                    return_value={
                        "id": 1,
                        **skill_data,
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                    }
                ),
            ):
                with patch(
                    "app.api.deps.user_crud.get_by_api_key",
                    new=AsyncMock(return_value=mock_user),
                ):
                    response = client.post(
                        "/api/v1/skills",
                        json=skill_data,
                        headers=admin_auth_headers,
                    )

        assert response.status_code == 201
        assert response.json()["name"] == "new_skill"
        assert response.json()["description"] == "A new test skill"

    def test_create_skill_already_exists(
        self, client, admin_auth_headers, mock_get_db, sample_skill
    ):
        """Test creating a skill that already exists."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=sample_skill),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_user),
            ):
                response = client.post(
                    "/api/v1/skills",
                    json={
                        "name": "test_skill",
                        "description": "Duplicate skill",
                        "content": "Content",
                    },
                    headers=admin_auth_headers,
                )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_skill_unauthorized(self, client, user_auth_headers):
        """Test creating a skill without admin privileges."""
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
                "/api/v1/skills",
                json={
                    "name": "new_skill",
                    "description": "A new skill",
                    "content": "Content",
                },
                headers=user_auth_headers,
            )

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_create_skill_no_auth(self, client):
        """Test creating a skill without authentication."""
        response = client.post(
            "/api/v1/skills",
            json={
                "name": "new_skill",
                "description": "A new skill",
                "content": "Content",
            },
        )

        # FastAPI returns 422 for missing required headers
        assert response.status_code in [401, 422]

    def test_create_skill_invalid_data(self, client, admin_auth_headers, mock_get_db):
        """Test creating a skill with invalid data."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.deps.user_crud.get_by_api_key",
            new=AsyncMock(return_value=mock_user),
        ):
            # Missing required field
            response = client.post(
                "/api/v1/skills",
                json={
                    "name": "new_skill",
                    # Missing description and content
                },
                headers=admin_auth_headers,
            )

        assert response.status_code == 422  # Validation error


class TestUpdateSkill:
    """Tests for PUT /api/v1/skills/{name} endpoint."""

    def test_update_skill_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully updating an existing skill."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        updated_skill = {
            "id": 1,
            "name": "test_skill",
            "description": "Updated description",
            "content": "Updated content",
            "version": "1.1",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }

        with patch(
            "app.api.v1.skills.skill_crud.update",
            new=AsyncMock(return_value=updated_skill),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_user),
            ):
                response = client.put(
                    "/api/v1/skills/test_skill",
                    json={
                        "description": "Updated description",
                        "version": "1.1",
                    },
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200
        assert response.json()["description"] == "Updated description"
        assert response.json()["version"] == "1.1"

    def test_update_skill_not_found(self, client, admin_auth_headers, mock_get_db):
        """Test updating a non-existent skill."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.skills.skill_crud.update", new=AsyncMock(return_value=None)
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_user),
            ):
                response = client.put(
                    "/api/v1/skills/nonexistent",
                    json={"description": "Updated"},
                    headers=admin_auth_headers,
                )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_skill_unauthorized(self, client, user_auth_headers):
        """Test updating a skill without admin privileges."""
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
            response = client.put(
                "/api/v1/skills/test_skill",
                json={"description": "Updated"},
                headers=user_auth_headers,
            )

        assert response.status_code == 403

    def test_update_skill_partial(self, client, admin_auth_headers, mock_get_db):
        """Test updating only some fields of a skill."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        updated_skill = {
            "id": 1,
            "name": "test_skill",
            "description": "Only description updated",
            "content": "Original content",
            "version": "1.0",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }

        with patch(
            "app.api.v1.skills.skill_crud.update",
            new=AsyncMock(return_value=updated_skill),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_user),
            ):
                response = client.put(
                    "/api/v1/skills/test_skill",
                    json={"description": "Only description updated"},
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200


class TestDeleteSkill:
    """Tests for DELETE /api/v1/skills/{name} endpoint."""

    def test_delete_skill_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully deleting a skill."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.skills.skill_crud.delete", new=AsyncMock(return_value=True)
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_user),
            ):
                response = client.delete(
                    "/api/v1/skills/test_skill",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 204

    def test_delete_skill_not_found(self, client, admin_auth_headers, mock_get_db):
        """Test deleting a non-existent skill."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.skills.skill_crud.delete", new=AsyncMock(return_value=False)
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_user),
            ):
                response = client.delete(
                    "/api/v1/skills/nonexistent",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_delete_skill_unauthorized(self, client, user_auth_headers):
        """Test deleting a skill without admin privileges."""
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
                "/api/v1/skills/test_skill",
                headers=user_auth_headers,
            )

        assert response.status_code == 403

    def test_delete_skill_no_auth(self, client):
        """Test deleting a skill without authentication."""
        response = client.delete("/api/v1/skills/test_skill")

        # FastAPI returns 422 for missing required headers
        assert response.status_code in [401, 422]
