"""Settings module for SecretMagic microservice."""

import os
from typing import Any

from src.database.postgres import PostgresConfig


class RedisConfig:
    """Redis configuration."""

    def __init__(self) -> None:
        self.host = os.getenv("MESSENGER_HOST", "messenger")
        self.port = int(os.getenv("MESSENGER_PORT", "6379"))
        self.db = int(os.getenv("MESSENGER_DB", "0"))
        self.consumer_group = f"secretmagic-{os.getenv('ENVIRONMENT', 'dev')}"
        self.subscribe_streams: list[str] = []
        self.publish_streams: dict[str, str] = {}


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

        # Redis
        self.redis = RedisConfig()
