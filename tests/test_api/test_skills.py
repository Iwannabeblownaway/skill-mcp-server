"""Tests for skills API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCreateSkill:
    """Tests for POST /api/v1/skills endpoint."""

    def test_create_skill_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully creating a new skill via JSON."""
        conn, cursor = mock_get_db

        skill_data = {
            "name": "new_skill",
            "description": "A new test skill",
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
                        "name": "new_skill",
                        "description": "A new test skill",
                        "path": "new_skill",
                        "version": "1.0",
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                    }
                ),
            ):
                with patch(
                    "app.api.deps.user_crud.get_by_api_key",
                    new=AsyncMock(return_value=mock_user),
                ):
                    with patch(
                        "app.api.v1.skills.SKILLS_DIR",
                        new_callable=lambda: MagicMock(),
                    ):
                        response = client.post(
                            "/api/v1/skills/json",
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
                    "/api/v1/skills/json",
                    json={
                        "name": "test_skill",
                        "description": "Duplicate skill",
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
            "path": "test_skill",
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
            "path": "test_skill",
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


class TestSkillDependencies:
    """Tests for GET /api/v1/skills/{name}/dependencies endpoint."""

    def test_get_dependencies_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully getting skill dependencies."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }
        mock_skill = {
            "id": 1,
            "name": "test_skill",
            "description": "Test skill",
            "path": "test_skill",
            "dependencies": ["https://mcp.sorftime.com", "https://mcp.example.com"],
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=mock_skill),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/skills/test_skill/dependencies",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_skill"
        assert len(data["dependencies"]) == 2

    def test_get_dependencies_not_found(self, client, admin_auth_headers, mock_get_db):
        """Test getting dependencies for non-existent skill."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/skills/nonexistent/dependencies",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 404

    def test_get_dependencies_unauthorized(self, client, user_auth_headers):
        """Test getting dependencies without admin privileges."""
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
            response = client.get(
                "/api/v1/skills/test_skill/dependencies",
                headers=user_auth_headers,
            )

        assert response.status_code == 403


class TestSkillFiles:
    """Tests for GET /api/v1/skills/{name}/files endpoint."""

    def test_list_skill_files_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully listing skill files."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }
        mock_skill = {
            "id": 1,
            "name": "test_skill",
            "description": "Test skill",
            "path": "test_skill",
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=mock_skill),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                with patch(
                    "app.api.v1.skills.SKILLS_DIR",
                    new=MagicMock(),
                ):
                    response = client.get(
                        "/api/v1/skills/test_skill/files",
                        headers=admin_auth_headers,
                    )

        assert response.status_code == 200
        data = response.json()
        assert "files" in data

    def test_list_skill_files_not_found(self, client, admin_auth_headers, mock_get_db):
        """Test listing files for non-existent skill."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/skills/nonexistent/files",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 404


class TestSkillSync:
    """Tests for POST /api/v1/skills/{name}/sync endpoint."""

    def test_sync_skill_not_found(self, client, admin_auth_headers, mock_get_db):
        """Test syncing non-existent skill."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.post(
                    "/api/v1/skills/nonexistent/sync",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 404

    def test_sync_skill_folder_not_found(self, client, admin_auth_headers, mock_get_db):
        """Test syncing skill with missing folder."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }
        mock_skill = {
            "id": 1,
            "name": "test_skill",
            "description": "Test skill",
            "path": "test_skill",
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=mock_skill),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                with patch(
                    "app.api.v1.skills.skill_crud.load_skill_folder_as_json",
                    new=MagicMock(return_value=None),
                ):
                    response = client.post(
                        "/api/v1/skills/test_skill/sync",
                        headers=admin_auth_headers,
                    )

        assert response.status_code == 404


class TestSkillList:
    """Tests for GET /api/v1/skills endpoint."""

    def test_list_skills_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully listing skills."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        skills_list = [
            {
                "id": 1,
                "name": "skill_1",
                "description": "First skill",
                "path": "skill_1",
                "status": "active",
            },
            {
                "id": 2,
                "name": "skill_2",
                "description": "Second skill",
                "path": "skill_2",
                "status": "draft",
            },
        ]

        with patch(
            "app.api.v1.skills.skill_crud.list_all",
            new=AsyncMock(return_value=skills_list),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/skills",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["skills"]) == 2
        assert data["total"] == 2

    def test_list_skills_unauthorized(self, client, user_auth_headers):
        """Test listing skills without admin privileges."""
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
            response = client.get(
                "/api/v1/skills",
                headers=user_auth_headers,
            )

        assert response.status_code == 403


class TestSkillContent:
    """Tests for GET /api/v1/skills/{name}/content endpoint."""

    def test_get_skill_content_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully getting skill content."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }
        mock_skill = {
            "id": 1,
            "name": "test_skill",
            "description": "Test skill",
            "path": "test_skill",
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=mock_skill),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                with patch(
                    "app.api.v1.skills.load_skill_content",
                    new=MagicMock(return_value="# Skill Content"),
                ):
                    response = client.get(
                        "/api/v1/skills/test_skill/content",
                        headers=admin_auth_headers,
                    )

        assert response.status_code == 200
        data = response.json()
        assert "content" in data

    def test_get_skill_content_not_found(self, client, admin_auth_headers, mock_get_db):
        """Test getting content for non-existent skill."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/skills/nonexistent/content",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 404


class TestUpdateSkillContent:
    """Tests for PUT /api/v1/skills/{name}/content endpoint."""

    def test_update_skill_content_success(
        self, client, admin_auth_headers, mock_get_db
    ):
        """Test successfully updating skill content."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        sample_skill = {
            "id": 1,
            "name": "test_skill",
            "description": "Test skill",
            "path": "test_skill",
            "version": "1.0",
        }

        new_content = "# Updated Skill\n\nNew content here."

        # Create a proper mock Path
        mock_path = MagicMock()
        mock_parent = MagicMock()
        mock_path.parent = mock_parent

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=sample_skill),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_user),
            ):
                with patch(
                    "app.api.v1.skills.skill_crud.get_skill_content_path",
                    return_value=mock_path,
                ):
                    with patch("pathlib.Path.mkdir", new_callable=MagicMock()):
                        with patch("builtins.open", MagicMock()):
                            with patch(
                                "pathlib.Path.write_text", new_callable=MagicMock()
                            ):
                                response = client.put(
                                    "/api/v1/skills/test_skill/content",
                                    json={"content": new_content},
                                    headers=admin_auth_headers,
                                )

        assert response.status_code == 200
        assert response.json()["message"] == "Content updated successfully"
        assert response.json()["name"] == "test_skill"

    def test_update_skill_content_not_found(
        self, client, admin_auth_headers, mock_get_db
    ):
        """Test updating content for non-existent skill."""
        conn, cursor = mock_get_db

        mock_user = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.skills.skill_crud.get_by_name",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_user),
            ):
                response = client.put(
                    "/api/v1/skills/nonexistent/content",
                    json={"content": "# Content"},
                    headers=admin_auth_headers,
                )

        assert response.status_code == 404

    def test_update_skill_content_unauthorized(self, client, user_auth_headers):
        """Test updating content without admin privileges."""
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
                "/api/v1/skills/test_skill/content",
                json={"content": "# Content"},
                headers=user_auth_headers,
            )

        assert response.status_code == 403
