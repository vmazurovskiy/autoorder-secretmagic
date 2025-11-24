"""Redis client - stub for now."""

from typing import Any


class RedisClient:
    """Stub RedisClient class."""

    def __init__(self, config: Any) -> None:
        pass

    async def connect(self) -> None:
        """Connect to Redis."""
        pass

    async def close(self) -> None:
        """Close Redis connection."""
        pass
