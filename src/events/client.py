"""Redis client for messenger (Redis Streams)."""

import asyncio
from typing import TYPE_CHECKING

import redis.asyncio as redis_async
from redis.asyncio.client import Redis

from src.logger.logger import get_logger
from src.logger.types import Category, param

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

    async def connect(self, max_retries: int = 10, initial_delay: float = 1.0) -> None:
        """
        Connect to Redis with retry logic.

        Args:
            max_retries: Maximum connection attempts (default 10)
            initial_delay: Initial delay between retries in seconds (default 1.0)

        Raises:
            ConnectionError: If unable to connect after max_retries
        """
        logger = get_logger().with_category(Category.MESSENGER)
        delay = initial_delay
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                self.redis = redis_async.Redis(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    decode_responses=True,
                    socket_keepalive=True,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                )

                # Проверяем подключение
                await self.redis.ping()  # type: ignore[misc]
                return  # Успешное подключение

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warn(
                        f"Redis connection attempt {attempt}/{max_retries} failed, retrying...",
                        param("host", self.config.host),
                        param("port", self.config.port),
                        param("delay", delay),
                        param("error", str(e)),
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 30.0)  # Exponential backoff, max 30s

        # Все попытки исчерпаны
        logger.error(
            f"Failed to connect to Redis after {max_retries} attempts",
            last_error,
            param("host", self.config.host),
            param("port", self.config.port),
        )
        raise ConnectionError(
            f"Failed to connect to Redis at {self.config.host}:{self.config.port} "
            f"after {max_retries} attempts"
        )

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
