"""Settings module for SecretMagic microservice."""

import os
from typing import Any

from src.database.postgres import PostgresConfig


class Settings:
    """Application settings."""

    def __init__(self) -> None:
        # Service info
        self.environment = os.getenv("ENVIRONMENT", "dev")
        self.service_name = os.getenv("SERVICE_NAME", "secretmagic")
        self.service_version = os.getenv("SERVICE_VERSION", "0.1.0")
        self.log_level = os.getenv("LOG_LEVEL", "debug")

        # PostgreSQL
        self.postgres = PostgresConfig()

        # Redis (stub for now)
        self.redis: Any = None
