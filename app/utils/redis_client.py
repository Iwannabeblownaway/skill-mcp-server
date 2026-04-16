"""Redis client module with singleton pattern for async Redis operations."""

import json
from typing import Any, Optional
import redis.asyncio as redis


class RedisClient:
    """Singleton Redis client wrapper for session data management."""

    _instance: Optional["RedisClient"] = None
    _client: Optional[redis.Redis] = None

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
            port: Redis server port.
            db: Redis database number.
            password: Redis authentication password.
            decode_responses: Whether to decode responses as strings.
        """
        if self._client is None:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=decode_responses,
            )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> redis.Redis:
        """Get the underlying Redis client.

        Raises:
            RuntimeError: If Redis client is not connected.
        """
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    async def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieve session data from Redis.

        Args:
            session_id: Unique session identifier.

        Returns:
            Session data as dictionary, or None if not found.
        """
        data = await self.client.get(f"session:{session_id}")
        if data is None:
            return None
        return json.loads(data)

    async def put_session(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: Optional[int] = 3600,
    ) -> None:
        """Store session data in Redis.

        Args:
            session_id: Unique session identifier.
            data: Session data to store.
            ttl: Time-to-live in seconds (default: 1 hour).
        """
        serialized = json.dumps(data)
        await self.client.setex(f"session:{session_id}", ttl, serialized)

    async def delete_session(self, session_id: str) -> None:
        """Delete session data from Redis.

        Args:
            session_id: Unique session identifier.
        """
        await self.client.delete(f"session:{session_id}")

    async def ping(self) -> bool:
        """Check Redis connection health.

        Returns:
            True if Redis is responsive, False otherwise.
        """
        try:
            return await self.client.ping()
        except Exception:
            return False


# Global singleton instance
redis_client = RedisClient()
