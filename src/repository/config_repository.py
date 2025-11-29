"""Configuration repository for PostgreSQL."""

from datetime import date, datetime

from psycopg2.extras import RealDictCursor

from src.database.postgres import PostgresClient
from src.domain.config import ConfigEntry
from src.logger.logger import get_logger
from src.logger.types import Category, param


class ConfigRepository:
    """Repository for global configuration in PostgreSQL."""

    def __init__(self, postgres_client: PostgresClient) -> None:
        """
        Initialize ConfigRepository.

        Args:
            postgres_client: PostgreSQL client instance
        """
        self.postgres = postgres_client
        self.logger = get_logger().with_category(Category.DATABASE)

    def get(self, key: str) -> ConfigEntry | None:
        """
        Get configuration entry by key.

        Args:
            key: Configuration key

        Returns:
            ConfigEntry or None if not found
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT key, value, description, updated_at, updated_by
                    FROM config
                    WHERE key = %s
                    """,
                    (key,),
                )
                row = cur.fetchone()

                if row is None:
                    return None

                return ConfigEntry(
                    key=row["key"],
                    value=row["value"],
                    description=row["description"],
                    updated_at=row["updated_at"],
                    updated_by=row["updated_by"],
                )
        finally:
            self.postgres.put_connection(conn)

    def get_value(self, key: str, default: str | None = None) -> str | None:
        """
        Get configuration value by key.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        entry = self.get(key)
        return entry.value if entry else default

    def get_date(self, key: str, default: date | None = None) -> date | None:
        """
        Get configuration value as date.

        Args:
            key: Configuration key (value format: YYYY-MM-DD)
            default: Default value if not found

        Returns:
            Date or default
        """
        value = self.get_value(key)
        if value is None:
            return default
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            self.logger.warn(
                f"Invalid date format for config key {key}",
                param("key", key),
                param("value", value),
            )
            return default

    def get_day_month(self, key: str) -> tuple[int, int] | None:
        """
        Get configuration value as day.month tuple.

        Args:
            key: Configuration key (value format: DD.MM)

        Returns:
            Tuple (day, month) or None
        """
        value = self.get_value(key)
        if value is None:
            return None
        try:
            parts = value.split(".")
            if len(parts) != 2:
                return None
            return int(parts[0]), int(parts[1])
        except ValueError:
            self.logger.warn(
                f"Invalid day.month format for config key {key}",
                param("key", key),
                param("value", value),
            )
            return None

    def set(self, key: str, value: str, updated_by: str = "system") -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
            updated_by: Who updated (system, admin, api)
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO config (key, value, updated_by, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = NOW()
                    """,
                    (key, value, updated_by),
                )
            conn.commit()

            self.logger.info(
                "Config updated",
                param("key", key),
                param("updated_by", updated_by),
            )
        except Exception as e:
            conn.rollback()
            self.logger.error(
                "Failed to update config",
                param("key", key),
                param("error", str(e)),
            )
            raise
        finally:
            self.postgres.put_connection(conn)

    def get_all(self) -> list[ConfigEntry]:
        """
        Get all configuration entries.

        Returns:
            List of ConfigEntry
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT key, value, description, updated_at, updated_by
                    FROM config
                    ORDER BY key
                    """
                )
                rows = cur.fetchall()

                return [
                    ConfigEntry(
                        key=row["key"],
                        value=row["value"],
                        description=row["description"],
                        updated_at=row["updated_at"],
                        updated_by=row["updated_by"],
                    )
                    for row in rows
                ]
        finally:
            self.postgres.put_connection(conn)
