"""Redis client module with singleton pattern for async Redis operations.

Includes in-memory fallback when Redis is unavailable.
"""

import json
import time
from typing import Any, Optional
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class InMemorySessionStore:
    """In-memory session store fallback when Redis is unavailable."""

    def __init__(self):
        self._store: dict[str, tuple[dict, float]] = {}  # session_id -> (data, expiry_time)

    async def get(self, session_id: str) -> Optional[dict]:
        """Get session data if not expired."""
        if session_id not in self._store:
            return None
        data, expiry = self._store[session_id]
        if time.time() > expiry:
            del self._store[session_id]
            return None
        return data

    async def setex(self, key: str, ttl: int, value: str) -> None:
        """Store session with TTL (key is stored as-is)."""
        self._store[key] = (json.loads(value), time.time() + ttl)

    async def delete(self, session_id: str) -> None:
        """Delete session (key is stored as-is)."""
        self._store.pop(session_id, None)

    async def ping(self) -> bool:
        """Always return True for in-memory store."""
        return True


class RedisClient:
    """Singleton Redis client wrapper for session data management."""

    _instance: Optional["RedisClient"] = None
    _client: Optional[redis.Redis] = None
    _memory_store: Optional[InMemorySessionStore] = None
    _use_memory: bool = False

    def __new__(cls) -> "RedisClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
    ) -> None:
        """Initialize Redis connection.

        Args:
            host: Redis server hostname.
            port: Redis port.
            db: Redis database number.
            password: Redis authentication password.
            decode_responses: Whether to decode responses as strings.
        """
        if not REDIS_AVAILABLE:
            logger.info("Redis not available, using in-memory session store")
            self._use_memory = True
            self._memory_store = InMemorySessionStore()
            return

        try:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=decode_responses,
            )
            # Test connection
            await self._client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory session store: {e}")
            self._use_memory = True
            self._memory_store = InMemorySessionStore()
            self._client = None

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> Any:
        """Get the underlying Redis client or memory store."""
        if self._use_memory:
            return self._memory_store
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    async def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieve session data from Redis or memory store."""
        if self._use_memory:
            return await self._memory_store.get(f"session:{session_id}")
        data = await self._client.get(f"session:{session_id}")
        if data is None:
            return None
        return json.loads(data)

    async def put_session(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: int = 3600,
    ) -> None:
        """Store session data in Redis or memory store."""
        serialized = json.dumps(data)
        if self._use_memory:
            await self._memory_store.setex(f"session:{session_id}", ttl, serialized)
        else:
            await self._client.setex(f"session:{session_id}", ttl, serialized)

    async def delete_session(self, session_id: str) -> None:
        """Delete session data from Redis or memory store."""
        if self._use_memory:
            await self._memory_store.delete(f"session:{session_id}")
        else:
            await self._client.delete(f"session:{session_id}")

    async def ping(self) -> bool:
        """Check connection health."""
        if self._use_memory:
            return True
        try:
            result = await self._client.ping()
            return bool(result)
        except Exception:
            return False


# Global singleton instance
redis_client = RedisClient()
