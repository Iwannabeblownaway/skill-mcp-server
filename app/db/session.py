"""Database connection pool and session management."""

import asyncio
from typing import AsyncIterator

import aiomysql
from contextlib import asynccontextmanager

from app.config import settings


class DatabasePool:
    """Singleton database connection pool manager."""

    _pool: aiomysql.Pool | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    async def get_pool(cls) -> aiomysql.Pool:
        """Get or create the database connection pool (double-check locking)."""
        if cls._pool is None:
            async with cls._lock:
                if cls._pool is None:
                    cls._pool = await aiomysql.create_pool(
                        host=settings.DB_HOST,
                        port=settings.DB_PORT,
                        user=settings.DB_USER,
                        password=settings.DB_PASSWORD,
                        db=settings.DB_NAME,
                        autocommit=True,
                        minsize=5,
                        maxsize=20,
                        charset="utf8mb4",
                    )
        assert cls._pool is not None, "Pool should be initialized"
        return cls._pool

    @classmethod
    async def close_pool(cls) -> None:
        """Close the database connection pool."""
        async with cls._lock:
            if cls._pool is not None:
                cls._pool.close()
                await cls._pool.wait_closed()
                cls._pool = None


@asynccontextmanager
async def get_db() -> AsyncIterator[aiomysql.Connection]:
    """Get a database connection from the pool.

    Yields:
        Database connection that auto-returns to pool on exit.

    Example:
        async with get_db() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
    """
    pool = await DatabasePool.get_pool()
    async with pool.acquire() as conn:
        try:
            yield conn
        finally:
            pass  # Connection returns to pool automatically
