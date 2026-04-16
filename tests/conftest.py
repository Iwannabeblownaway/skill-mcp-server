"""Test configuration and fixtures for skill-mcp-server."""

import asyncio
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI


# ==================== Database Fixtures ====================


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection for testing."""
    conn = MagicMock()
    cursor = AsyncMock()
    conn.cursor.return_value = cursor

    # Configure cursor as async context manager
    cursor.__aenter__ = AsyncMock(return_value=cursor)
    cursor.__aexit__ = AsyncMock(return_value=None)

    return conn, cursor


@pytest.fixture
def mock_db_pool(mock_db_connection):
    """Create a mock database pool for testing."""
    conn, cursor = mock_db_connection
    pool = MagicMock()
    pool.acquire.return_value = conn
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)

    return pool


@pytest_asyncio.fixture
async def mock_get_db(mock_db_connection):
    """Mock the get_db function to return a mock connection."""
    conn, cursor = mock_db_connection

    @asynccontextmanager
    async def _mock_get_db():
        yield conn

    with patch("app.db.session.get_db", _mock_get_db):
        with patch("app.services.skill_service.get_db", _mock_get_db):
            with patch("app.services.user_service.get_db", _mock_get_db):
                with patch("app.api.deps.get_db", _mock_get_db):
                    with patch("app.api.v1.skills.get_db", _mock_get_db):
                        with patch("app.api.v1.users.get_db", _mock_get_db):
                            with patch("app.api.v1.auth.get_db", _mock_get_db):
                                yield conn, cursor


@pytest.fixture
def sqlite_in_memory_db():
    """Create an in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Create test tables
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Skills table
    cursor.execute("""
        CREATE TABLE skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL,
            content TEXT NOT NULL,
            version TEXT DEFAULT '1.0',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # User skills table
    cursor.execute("""
        CREATE TABLE user_skills (
            user_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, skill_id)
        )
    """)

    # Skill calls table
    cursor.execute("""
        CREATE TABLE skill_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            call_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL,
            error_message TEXT,
            duration_ms INTEGER
        )
    """)

    conn.commit()

    yield conn

    conn.close()


# ==================== Redis Fixtures ====================


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.connect = AsyncMock(return_value=None)
    redis.disconnect = AsyncMock(return_value=None)

    return redis


@pytest.fixture
def mock_redis_patch(mock_redis_client):
    """Patch Redis client globally."""
    with patch("app.utils.redis_client.redis_client", mock_redis_client):
        with patch("app.main.redis_client", mock_redis_client):
            yield mock_redis_client


# ==================== Sample Data Fixtures ====================


@pytest.fixture
def sample_user():
    """Return a sample user dictionary."""
    return {
        "id": 1,
        "external_id": "user_001",
        "username": "TestUser",
        "api_key": "test_api_key_12345",
        "role": "user",
        "created_at": datetime.now(),
    }


@pytest.fixture
def sample_admin():
    """Return a sample admin user dictionary."""
    return {
        "id": 2,
        "external_id": "admin_001",
        "username": "Admin",
        "api_key": "admin_api_key_12345",
        "role": "admin",
        "created_at": datetime.now(),
    }


@pytest.fixture
def sample_skill():
    """Return a sample skill dictionary."""
    return {
        "id": 1,
        "name": "test_skill",
        "description": "A test skill for unit testing",
        "content": "# Test Skill\n\nThis is a test skill content.",
        "version": "1.0",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture
def sample_skills_list():
    """Return a list of sample skills."""
    return [
        {
            "id": 1,
            "name": "skill_1",
            "description": "First test skill",
            "content": "Content for skill 1",
            "version": "1.0",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
        {
            "id": 2,
            "name": "skill_2",
            "description": "Second test skill",
            "content": "Content for skill 2",
            "version": "1.0",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    ]


@pytest.fixture
def sample_call_log():
    """Return a sample call log entry."""
    return {
        "id": 1,
        "user_id": 1,
        "skill_id": 1,
        "call_time": datetime.now(),
        "status": "success",
        "error_message": None,
        "duration_ms": 150,
    }


# ==================== Mock Response Fixtures ====================


@pytest.fixture
def mock_user_crud():
    """Mock user CRUD operations."""
    with patch("app.db.crud.user") as mock:
        yield mock


@pytest.fixture
def mock_skill_crud():
    """Mock skill CRUD operations."""
    with patch("app.db.crud.skill") as mock:
        yield mock


@pytest.fixture
def mock_user_skill_crud():
    """Mock user_skill CRUD operations."""
    with patch("app.db.crud.user_skill") as mock:
        yield mock


@pytest.fixture
def mock_call_log_crud():
    """Mock call_log CRUD operations."""
    with patch("app.db.crud.call_log") as mock:
        yield mock


# ==================== CRUD Mock Helper Fixtures ====================


@pytest.fixture
def mock_crud_operations(
    mock_user_crud, mock_skill_crud, mock_user_skill_crud, mock_call_log_crud
):
    """Setup all CRUD mocks with default behaviors."""
    # User CRUD defaults
    mock_user_crud.get_by_api_key = AsyncMock()
    mock_user_crud.get_by_id = AsyncMock()
    mock_user_crud.create = AsyncMock()
    mock_user_crud.list_users = AsyncMock()

    # Skill CRUD defaults
    mock_skill_crud.get_by_name = AsyncMock()
    mock_skill_crud.get_by_id = AsyncMock()
    mock_skill_crud.create = AsyncMock()
    mock_skill_crud.update = AsyncMock()
    mock_skill_crud.delete = AsyncMock()
    mock_skill_crud.list_all = AsyncMock()

    # UserSkill CRUD defaults
    mock_user_skill_crud.grant = AsyncMock()
    mock_user_skill_crud.revoke = AsyncMock()
    mock_user_skill_crud.get_user_skills = AsyncMock()
    mock_user_skill_crud.has_skill = AsyncMock()

    # CallLog CRUD defaults
    mock_call_log_crud.create_log = AsyncMock()

    yield {
        "user": mock_user_crud,
        "skill": mock_skill_crud,
        "user_skill": mock_user_skill_crud,
        "call_log": mock_call_log_crud,
    }


# ==================== FastAPI Test Client ====================


@pytest.fixture
def app(mock_get_db, mock_redis_patch):
    """Create a FastAPI app for testing with mocked dependencies."""
    from app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app.

    Patches the MCP session_manager.run() context manager to avoid
    'can only be called once per instance' errors when creating multiple
    TestClient instances.
    """
    from unittest.mock import AsyncMock, MagicMock, patch
    from contextlib import asynccontextmanager

    # Create a mock context manager that does nothing
    @asynccontextmanager
    async def mock_run():
        yield

    # Patch session_manager.run to use our mock
    with patch("app.mcp.server.session_manager.run", mock_run):
        with TestClient(app) as test_client:
            yield test_client


# ==================== Authentication Headers ====================


@pytest.fixture
def user_auth_headers(sample_user):
    """Return authentication headers for a regular user."""
    return {"X-API-Key": sample_user["api_key"]}


@pytest.fixture
def admin_auth_headers(sample_admin):
    """Return authentication headers for an admin user."""
    return {"X-API-Key": sample_admin["api_key"]}
