"""Settings module - stub for now."""

from typing import Any


class Settings:
    """Stub Settings class."""

    def __init__(self) -> None:
        self.environment = "dev"
        self.service_name = "secretmagic"
        self.service_version = "0.1.0"
        self.postgres: Any = None
        self.redis: Any = None
