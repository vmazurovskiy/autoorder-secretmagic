"""Event processor - stub for now."""

from typing import Any


class EventProcessor:
    """Stub EventProcessor class."""

    def __init__(
        self, postgres: Any, publisher: Any, settings: Any
    ) -> None:
        pass

    async def process_event(self, event: Any) -> None:
        """Process event."""
        pass
