"""StarRocks client for SecretMagic microservice.

StarRocks использует MySQL-протокол, поэтому подключаемся через PyMySQL.
Порт по умолчанию: 9030 (FE query port).
"""

import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from src.logger.logger import get_logger
from src.logger.types import Category, param


class StarRocksConfig:
    """StarRocks connection configuration."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        connect_timeout: int = 10,
        read_timeout: int = 30,
        write_timeout: int = 30,
        charset: str = "utf8mb4",
    ) -> None:
        self.host = host or os.getenv("STARROCKS_HOST", "starrocks")
        self.port = port or int(os.getenv("STARROCKS_PORT", "9030"))
        self.database = database or os.getenv("STARROCKS_DATABASE", "autoorder_data")
        self.user = user or self._read_user()
        self.password = password or self._read_password()
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.charset = charset

    @staticmethod
    def _read_user() -> str:
        """Read user from Docker secret or env."""
        secret_file = "/run/secrets/starrocks_user"
        if os.path.exists(secret_file):
            with open(secret_file) as f:
                return f.read().strip()
        return os.getenv("STARROCKS_USER", "secretmagic")

    @staticmethod
    def _read_password() -> str:
        """Read password from Docker secret or env."""
        secret_file = "/run/secrets/starrocks_password"
        if os.path.exists(secret_file):
            with open(secret_file) as f:
                return f.read().strip()
        return os.getenv("STARROCKS_PASSWORD", "")

    def to_dict(self) -> dict[str, Any]:
        """Convert config to PyMySQL connection kwargs."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "charset": self.charset,
            "connect_timeout": self.connect_timeout,
            "read_timeout": self.read_timeout,
            "write_timeout": self.write_timeout,
            "cursorclass": DictCursor,
            "autocommit": True,
        }


class StarRocksClient:
    """StarRocks client with connection management.

    StarRocks не поддерживает prepared statements для INSERT,
    поэтому используем simple queries с параметризацией через PyMySQL.
    """

    def __init__(self, config: StarRocksConfig | None = None) -> None:
        """
        Initialize StarRocks client.

        Args:
            config: StarRocksConfig instance or None for defaults
        """
        self.config = config or StarRocksConfig()
        self._connection: Connection | None = None
        self.logger = get_logger().with_category(Category.STARROCKS)

    async def connect(self) -> None:
        """Connect to StarRocks."""
        try:
            self._connection = pymysql.connect(**self.config.to_dict())
            self.logger.info(
                "Connected to StarRocks",
                param("host", self.config.host),
                param("port", self.config.port),
                param("database", self.config.database),
            )
        except pymysql.Error as e:
            self.logger.error(
                "Failed to connect to StarRocks",
                e,
                param("host", self.config.host),
                param("port", self.config.port),
            )
            raise ConnectionError(f"Failed to connect to StarRocks: {e}") from e

    async def close(self) -> None:
        """Close StarRocks connection."""
        if self._connection:
            try:
                self._connection.close()
                self.logger.info("StarRocks connection closed")
            except pymysql.Error:
                pass
            finally:
                self._connection = None

    def _ensure_connected(self) -> Connection:
        """Ensure we have a valid connection, reconnect if needed."""
        if self._connection is None:
            raise RuntimeError("StarRocks not connected. Call connect() first.")

        # Check if connection is still alive, reconnect if needed
        try:
            self._connection.ping(reconnect=True)
        except pymysql.Error as e:
            self.logger.warn(
                "StarRocks connection lost, reconnecting...",
                param("error", str(e)),
            )
            self._connection = pymysql.connect(**self.config.to_dict())

        return self._connection

    @contextmanager
    def cursor(self) -> Generator[DictCursor, None, None]:
        """Get cursor context manager."""
        conn = self._ensure_connected()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> int:
        """
        Execute query without returning results.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Number of affected rows
        """
        with self.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount

    def fetch_one(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> dict[str, Any] | None:
        """
        Execute query and fetch one result.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Dict with column names as keys, or None
        """
        with self.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()  # type: ignore[return-value]

    def fetch_all(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute query and fetch all results.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            List of dicts with column names as keys
        """
        with self.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()  # type: ignore[return-value]

    def ping(self) -> bool:
        """Check if connection is alive."""
        try:
            self._ensure_connected()
            return True
        except (pymysql.Error, RuntimeError):
            return False
