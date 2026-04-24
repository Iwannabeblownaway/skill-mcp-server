"""Tests for admin session authentication."""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSessionManagement:
    """Tests for session management functions."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis = AsyncMock()
        redis.get_session = AsyncMock(return_value=None)
        redis.put_session = AsyncMock(return_value=None)
        redis.delete_session = AsyncMock(return_value=None)
        redis.ping = AsyncMock(return_value=True)
        return redis

    @pytest.mark.asyncio
    async def test_create_admin_session(self, mock_redis, sample_admin):
        """Test creating an admin session stores correct data."""
        with patch("app.admin.router.redis_client", mock_redis):
            from app.admin.router import create_admin_session

            session_id = await create_admin_session(sample_admin)

            assert session_id is not None
            assert len(session_id) > 20  # Should be a secure token
            mock_redis.put_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_admin_session_exists(self, mock_redis, sample_admin):
        """Test getting an existing session."""
        session_data = {
            "user_id": sample_admin["id"],
            "username": sample_admin["username"],
            "role": sample_admin["role"],
        }
        mock_redis.get_session = AsyncMock(return_value=session_data)

        with patch("app.admin.router.redis_client", mock_redis):
            from app.admin.router import get_admin_session

            result = await get_admin_session("test_session_id")

            assert result == session_data
            mock_redis.get_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_admin_session_not_found(self, mock_redis):
        """Test getting a non-existent session returns None."""
        mock_redis.get_session = AsyncMock(return_value=None)

        with patch("app.admin.router.redis_client", mock_redis):
            from app.admin.router import get_admin_session

            result = await get_admin_session("nonexistent_session")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_admin_session_empty_id(self, mock_redis):
        """Test getting session with empty ID returns None."""
        from app.admin.router import get_admin_session

        result = await get_admin_session("")
        assert result is None

        result = await get_admin_session(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_admin_session(self, mock_redis):
        """Test deleting an admin session."""
        with patch("app.admin.router.redis_client", mock_redis):
            from app.admin.router import delete_admin_session

            await delete_admin_session("test_session_id")

            mock_redis.delete_session.assert_called_once_with("admin:session:test_session_id")

    @pytest.mark.asyncio
    async def test_delete_admin_session_empty_id(self, mock_redis):
        """Test deleting with empty ID doesn't call Redis."""
        from app.admin.router import delete_admin_session

        await delete_admin_session("")
        mock_redis.delete_session.assert_not_called()

        await delete_admin_session(None)
        mock_redis.delete_session.assert_not_called()


class TestRequireAdmin:
    """Tests for require_admin dependency."""

    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        request = MagicMock()
        request.cookies.get = MagicMock(return_value=None)
        return request

    @pytest.mark.asyncio
    async def test_require_admin_no_cookie(self, mock_request):
        """Test require_admin redirects when no session cookie."""
        from fastapi import HTTPException

        with patch("app.admin.router.get_session_id", return_value=None):
            from app.admin.router import require_admin

            with pytest.raises(HTTPException) as exc_info:
                await require_admin(mock_request)

            assert exc_info.value.status_code == 303
            assert exc_info.value.headers["Location"] == "/admin/login"

    @pytest.mark.asyncio
    async def test_require_admin_invalid_session(self, mock_request):
        """Test require_admin redirects when session is invalid."""
        from fastapi import HTTPException

        mock_request.cookies.get = MagicMock(return_value="invalid_session")

        with patch("app.admin.router.get_session_id", return_value="invalid_session"):
            with patch("app.admin.router.get_admin_session", new=AsyncMock(return_value=None)):
                from app.admin.router import require_admin

                with pytest.raises(HTTPException) as exc_info:
                    await require_admin(mock_request)

                assert exc_info.value.status_code == 303


class TestLoginPage:
    """Tests for login page rendering."""

    def test_login_page_render(self, client, mock_redis_patch):
        """Test GET /admin/login renders login page."""
        response = client.get("/admin/login")

        assert response.status_code == 200
        assert "登录" in response.text
        assert "API Key" in response.text

    def test_login_page_has_csrf_token(self, client, mock_redis_patch):
        """Test login page has form token."""
        response = client.get("/admin/login")

        assert response.status_code == 200
        assert 'method="POST"' in response.text
        assert 'name="api_key"' in response.text


class TestProtectedRoutes:
    """Tests for protected admin routes redirect to login."""

    def test_dashboard_requires_auth(self, client, mock_redis_patch):
        """Test /admin/ redirects to login when not authenticated."""
        with patch("app.admin.router.get_session_id", return_value=None):
            response = client.get("/admin/", follow_redirects=False)

            assert response.status_code == 303
            assert "/admin/login" in response.headers.get("location", "")

    def test_users_list_requires_auth(self, client, mock_redis_patch):
        """Test /admin/users redirects to login when not authenticated."""
        with patch("app.admin.router.get_session_id", return_value=None):
            response = client.get("/admin/users", follow_redirects=False)

            assert response.status_code == 303

    def test_skills_list_requires_auth(self, client, mock_redis_patch):
        """Test /admin/skills redirects to login when not authenticated."""
        with patch("app.admin.router.get_session_id", return_value=None):
            response = client.get("/admin/skills", follow_redirects=False)

            assert response.status_code == 303

    def test_authorizations_requires_auth(self, client, mock_redis_patch):
        """Test /admin/authorizations redirects to login when not authenticated."""
        with patch("app.admin.router.get_session_id", return_value=None):
            response = client.get("/admin/authorizations", follow_redirects=False)

            assert response.status_code == 303

    def test_logs_requires_auth(self, client, mock_redis_patch):
        """Test /admin/logs redirects to login when not authenticated."""
        with patch("app.admin.router.get_session_id", return_value=None):
            response = client.get("/admin/logs", follow_redirects=False)

            assert response.status_code == 303

    def test_user_create_form_requires_auth(self, client, mock_redis_patch):
        """Test /admin/users/create GET requires auth."""
        with patch("app.admin.router.get_session_id", return_value=None):
            response = client.get("/admin/users/create", follow_redirects=False)

            assert response.status_code == 303

    def test_skill_create_form_requires_auth(self, client, mock_redis_patch):
        """Test /admin/skills/create GET requires auth."""
        with patch("app.admin.router.get_session_id", return_value=None):
            response = client.get("/admin/skills/create", follow_redirects=False)

            assert response.status_code == 303


class TestLogout:
    """Tests for logout functionality."""

    def test_logout_deletes_session(self, client, mock_redis_patch):
        """Test /admin/logout deletes session and redirects."""
        with patch("app.admin.router.get_session_id", return_value="test_session"):
            with patch("app.admin.router.delete_admin_session", new=AsyncMock(return_value=None)):
                response = client.get("/admin/logout", follow_redirects=False)

                assert response.status_code == 303
                assert "/admin/login" in response.headers.get("location", "")

    def test_logout_deletes_cookie(self, client, mock_redis_patch):
        """Test logout response deletes session cookie."""
        with patch("app.admin.router.get_session_id", return_value="test_session"):
            with patch("app.admin.router.delete_admin_session", new=AsyncMock(return_value=None)):
                response = client.get("/admin/logout", follow_redirects=False)

                # Cookie should be deleted
                assert "admin_session" in response.headers.get("set-cookie", "")


class TestSessionConfiguration:
    """Tests for session configuration."""

    def test_session_ttl_from_config(self):
        """Test that ADMIN_SESSION_TTL uses config value."""
        from app.config import settings

        # Default should be 86400 (24 hours)
        assert settings.ADMIN_SESSION_TTL == 86400

    def test_session_ttl_in_router(self):
        """Test that router uses ADMIN_SESSION_TTL from settings."""
        from app.admin.router import ADMIN_SESSION_TTL
        from app.config import settings

        assert ADMIN_SESSION_TTL == settings.ADMIN_SESSION_TTL

    def test_session_cookie_name(self):
        """Test session cookie name is set correctly."""
        from app.admin.router import SESSION_COOKIE_NAME

        assert SESSION_COOKIE_NAME == "admin_session"

    def test_session_key_prefix(self):
        """Test session key prefix is set correctly."""
        from app.admin.router import SESSION_KEY_PREFIX

        assert SESSION_KEY_PREFIX == "admin:session:"