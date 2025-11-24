"""Event subscriber - stub for now."""

from collections.abc import Awaitable, Callable
from typing import Any


class EventSubscriber:
    """Stub EventSubscriber class."""

    def __init__(self, redis_client: Any, consumer_group: Any, streams: Any) -> None:
        pass

    async def consume(self, handler: Callable[[Any], Awaitable[None]]) -> None:
        """Consume events."""
        pass

    async def stop(self) -> None:
        """Stop consuming events."""
        pass
