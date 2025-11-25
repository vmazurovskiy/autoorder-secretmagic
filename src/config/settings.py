"""Settings module for SecretMagic microservice."""

import os

from src.database.postgres import PostgresConfig


class RedisConfig:
    """Redis configuration."""

    def __init__(self) -> None:
        self.host = os.getenv("MESSENGER_HOST", "messenger")
        self.port = int(os.getenv("MESSENGER_PORT", "6379"))
        self.db = int(os.getenv("MESSENGER_DB", "0"))
        self.password = self._read_password()
        self.consumer_group = f"secretmagic-{os.getenv('ENVIRONMENT', 'dev')}"

        # Streams для подписки (читаем события от integrator)
        self.subscribe_streams: list[str] = [
            "clients-updates",  # Конфигурация клиентов
            # В будущем: sales-updates, stock-updates, bom-updates, и т.д.
        ]

        # Streams для публикации (пока не используется)
        self.publish_streams: dict[str, str] = {}

    def _read_password(self) -> str | None:
        """Read Redis password from Docker secret or environment."""
        secret_path = "/run/secrets/redis_password"
        try:
            with open(secret_path) as f:
                return f.read().strip()
        except FileNotFoundError:
            return os.getenv("MESSENGER_PASSWORD")


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
