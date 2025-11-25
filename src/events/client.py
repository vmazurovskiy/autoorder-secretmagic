"""Redis client for messenger (Redis Streams)."""

from typing import TYPE_CHECKING

import redis.asyncio as redis_async
from redis.asyncio.client import Redis

if TYPE_CHECKING:
    from src.config.settings import RedisConfig


class RedisClient:
    """Redis client for connecting to messenger."""

    def __init__(self, config: "RedisConfig") -> None:
        """
        Initialize Redis client.

        Args:
            config: Redis configuration with host, port, db
        """
        self.config = config
        self.redis: Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self.redis = redis_async.Redis(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            decode_responses=True,  # Автоматически декодировать bytes в str
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )

        # Проверяем подключение
        await self.redis.ping()  # type: ignore[misc]

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None

    def get_redis(self) -> Redis:
        """
        Get Redis client instance.

        Returns:
            Redis client

        Raises:
            RuntimeError: If not connected
        """
        if self.redis is None:
            raise RuntimeError("RedisClient not connected. Call connect() first.")
        return self.redis
