"""Tests for logs API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch


class TestListLogs:
    """Tests for GET /api/v1/logs endpoint."""

    def test_list_logs_success(self, client, admin_auth_headers, mock_get_db):
        """Test successfully listing call logs."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        logs_list = [
            {
                "id": 1,
                "user_id": 1,
                "skill_id": 1,
                "skill_name": "test_skill",
                "call_time": "2024-01-01T10:00:00",
                "status": "success",
                "error_message": None,
                "duration_ms": 150,
            },
            {
                "id": 2,
                "user_id": 1,
                "skill_id": 1,
                "skill_name": "test_skill",
                "call_time": "2024-01-01T09:00:00",
                "status": "failure",
                "error_message": "Permission denied",
                "duration_ms": 50,
            },
        ]

        with patch(
            "app.api.v1.logs.call_log_crud.list_logs",
            new=AsyncMock(return_value=(logs_list, 2)),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/logs",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 2
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_logs_filter_by_user(self, client, admin_auth_headers, mock_get_db):
        """Test listing logs filtered by user ID."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        user_logs = [
            {
                "id": 1,
                "user_id": 1,
                "skill_id": 1,
                "skill_name": "test_skill",
                "call_time": "2024-01-01T10:00:00",
                "status": "success",
                "error_message": None,
                "duration_ms": 150,
            },
        ]

        with patch(
            "app.api.v1.logs.call_log_crud.list_logs",
            new=AsyncMock(return_value=(user_logs, 1)),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/logs?user_id=1",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["logs"][0]["user_id"] == 1

    def test_list_logs_filter_by_skill(self, client, admin_auth_headers, mock_get_db):
        """Test listing logs filtered by skill name."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        skill_logs = [
            {
                "id": 1,
                "user_id": 1,
                "skill_id": 1,
                "skill_name": "mcp-builder",
                "call_time": "2024-01-01T10:00:00",
                "status": "success",
                "error_message": None,
                "duration_ms": 150,
            },
        ]

        with patch(
            "app.api.v1.logs.call_log_crud.list_logs",
            new=AsyncMock(return_value=(skill_logs, 1)),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/logs?skill_name=mcp-builder",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200

    def test_list_logs_filter_by_time_range(self, client, admin_auth_headers, mock_get_db):
        """Test listing logs filtered by time range."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        time_logs = [
            {
                "id": 1,
                "user_id": 1,
                "skill_id": 1,
                "skill_name": "test_skill",
                "call_time": "2024-01-01T12:00:00",
                "status": "success",
                "error_message": None,
                "duration_ms": 150,
            },
        ]

        with patch(
            "app.api.v1.logs.call_log_crud.list_logs",
            new=AsyncMock(return_value=(time_logs, 1)),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/logs?start_time=2024-01-01T00:00:00&end_time=2024-01-01T23:59:59",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200

    def test_list_logs_pagination(self, client, admin_auth_headers, mock_get_db):
        """Test listing logs with pagination."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.logs.call_log_crud.list_logs",
            new=AsyncMock(return_value=([], 0)),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/logs?page=2&page_size=10",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    def test_list_logs_empty(self, client, admin_auth_headers, mock_get_db):
        """Test listing logs when none exist."""
        conn, cursor = mock_get_db

        mock_admin = {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "api_key": "admin_key",
        }

        with patch(
            "app.api.v1.logs.call_log_crud.list_logs",
            new=AsyncMock(return_value=([], 0)),
        ):
            with patch(
                "app.api.deps.user_crud.get_by_api_key",
                new=AsyncMock(return_value=mock_admin),
            ):
                response = client.get(
                    "/api/v1/logs",
                    headers=admin_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []
        assert data["total"] == 0

    def test_list_logs_unauthorized(self, client, user_auth_headers):
        """Test listing logs without admin privileges."""
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
                "/api/v1/logs",
                headers=user_auth_headers,
            )

        assert response.status_code == 403

    def test_list_logs_no_auth(self, client):
        """Test listing logs without authentication."""
        response = client.get("/api/v1/logs")

        # FastAPI returns 422 for missing required headers
        assert response.status_code in [401, 422]

    def test_list_logs_invalid_page(self, client, admin_auth_headers):
        """Test listing logs with invalid page number."""
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
            response = client.get(
                "/api/v1/logs?page=0",
                headers=admin_auth_headers,
            )

        assert response.status_code == 422

    def test_list_logs_invalid_page_size(self, client, admin_auth_headers):
        """Test listing logs with invalid page size."""
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
            # Page size too large
            response = client.get(
                "/api/v1/logs?page_size=200",
                headers=admin_auth_headers,
            )

        assert response.status_code == 422