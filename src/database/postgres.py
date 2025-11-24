"""PostgreSQL client - stub for now."""

from typing import Any


class PostgresClient:
    """Stub PostgresClient class."""

    def __init__(self, config: Any) -> None:
        pass

    async def connect(self) -> None:
        """Connect to database."""
        pass

    async def close(self) -> None:
        """Close database connection."""
        pass
