"""Tests for in-memory session store fallback."""

import pytest
import sys
import time
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils import redis_client


class TestInMemorySessionStore:
    """Tests for InMemorySessionStore."""

    @pytest.fixture
    def store(self):
        """Create a fresh in-memory session store."""
        from app.utils.redis_client import InMemorySessionStore
        return InMemorySessionStore()

    @pytest.mark.asyncio
    async def test_set_and_get(self, store):
        """Test basic set and get operations."""
        await store.setex("test_key", 3600, '{"user_id": 1}')
        result = await store.get("test_key")
        assert result == {"user_id": 1}

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        """Test getting non-existent key returns None."""
        result = await store.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, store):
        """Test delete operation."""
        await store.setex("delete_key", 3600, '{"data": "test"}')
        await store.delete("delete_key")
        result = await store.get("delete_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_expiry(self, store):
        """Test that expired sessions are deleted."""
        # Set a session with very short TTL
        await store.setex("expire_key", 1, '{"data": "test"}')
        # Should exist initially
        result = await store.get("expire_key")
        assert result == {"data": "test"}
        # Wait for expiry
        time.sleep(1.1)
        result = await store.get("expire_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_ping(self, store):
        """Test ping returns True."""
        result = await store.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, store):
        """Test deleting non-existent key doesn't raise."""
        await store.delete("nonexistent")
        # Should not raise any exception

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, store):
        """Test storing multiple sessions."""
        await store.setex("session1", 3600, '{"id": 1}')
        await store.setex("session2", 3600, '{"id": 2}')
        await store.setex("session3", 3600, '{"id": 3}')

        assert await store.get("session1") == {"id": 1}
        assert await store.get("session2") == {"id": 2}
        assert await store.get("session3") == {"id": 3}

    @pytest.mark.asyncio
    async def test_overwrite_session(self, store):
        """Test overwriting existing session."""
        await store.setex("same_key", 3600, '{"version": 1}')
        await store.setex("same_key", 3600, '{"version": 2}')
        result = await store.get("same_key")
        assert result == {"version": 2}


class TestRedisClientFallback:
    """Tests for Redis client falling back to in-memory store."""

    @pytest.fixture
    def reset_client(self):
        """Reset the RedisClient singleton before each test."""
        from app.utils import redis_client
        redis_client.RedisClient._instance = None
        redis_client.RedisClient._client = None
        redis_client.RedisClient._memory_store = None
        redis_client.RedisClient._use_memory = False
        yield
        # Cleanup
        redis_client.RedisClient._instance = None

    @pytest.mark.asyncio
    async def test_uses_memory_when_redis_unavailable(self, reset_client):
        """Test that client uses in-memory store when Redis fails."""
        client = redis_client.RedisClient()
        await client.connect(host="nonexistent", port=9999)

        assert client._use_memory is True
        assert client._memory_store is not None

    @pytest.mark.asyncio
    async def test_memory_store_operations_work(self, reset_client):
        """Test that session operations work with memory store."""
        client = redis_client.RedisClient()
        await client.connect(host="nonexistent", port=9999)

        # Should use memory store
        await client.put_session("test_session", {"user_id": 123}, ttl=3600)
        result = await client.get_session("test_session")
        assert result == {"user_id": 123}

        await client.delete_session("test_session")
        result = await client.get_session("test_session")
        assert result is None

    @pytest.mark.asyncio
    async def test_ping_with_memory(self, reset_client):
        """Test ping returns True with memory store."""
        client = redis_client.RedisClient()
        await client.connect(host="nonexistent", port=9999)

        result = await client.ping()
        assert result is True
