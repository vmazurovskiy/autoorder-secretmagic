"""Settings module for SecretMagic microservice."""

import os

from src.database.postgres import PostgresConfig
from src.database.starrocks import StarRocksConfig


class YandexConfig:
    """Yandex API configuration (Geocoder)."""

    def __init__(self) -> None:
        self.geocoder_api_key = self._read_api_key()

    def _read_api_key(self) -> str | None:
        """Read Yandex Geocoder API key from Docker secret or environment."""
        secret_path = "/run/secrets/yandex_geocoder_api_key"
        try:
            with open(secret_path) as f:
                return f.read().strip()
        except FileNotFoundError:
            return os.getenv("YANDEX_GEOCODER_API_KEY")

    @property
    def is_configured(self) -> bool:
        """Check if Yandex Geocoder is configured."""
        return bool(self.geocoder_api_key)


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
            "sales-updates",  # Обновление продаж
            # В будущем: stock-updates, bom-updates, и т.д.
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

        # StarRocks (аналитическая БД)
        self.starrocks = StarRocksConfig()

        # Yandex APIs (Geocoder)
        self.yandex = YandexConfig()
