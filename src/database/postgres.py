"""PostgreSQL client for SecretMagic microservice."""

import os
from typing import Any

from psycopg2.extensions import connection as Connection
from psycopg2.pool import ThreadedConnectionPool


class PostgresConfig:
    """PostgreSQL connection configuration."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        min_conn: int = 2,
        max_conn: int = 10,
    ) -> None:
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.port = port or int(os.getenv("DB_PORT", "5432"))
        self.database = database or os.getenv("DB_NAME", "secretmagic")
        self.user = user or os.getenv("DB_USER", "secretmagic")
        self.password = password or self._read_password()
        self.min_conn = min_conn
        self.max_conn = max_conn

    @staticmethod
    def _read_password() -> str:
        """Read password from Docker secret or env."""
        secret_file = "/run/secrets/db_password"
        if os.path.exists(secret_file):
            with open(secret_file) as f:
                return f.read().strip()
        return os.getenv("DB_PASSWORD", "secretmagic")

    @property
    def dsn(self) -> str:
        """Get PostgreSQL DSN."""
        return (
            f"host={self.host} "
            f"port={self.port} "
            f"dbname={self.database} "
            f"user={self.user} "
            f"password={self.password}"
        )


class PostgresClient:
    """PostgreSQL client with connection pooling."""

    def __init__(self, config: PostgresConfig | Any) -> None:
        """
        Initialize PostgreSQL client.

        Args:
            config: PostgresConfig or config dict
        """
        if isinstance(config, dict):
            self.config = PostgresConfig(**config)
        elif config is None:
            self.config = PostgresConfig()
        else:
            self.config = config

        self.pool: ThreadedConnectionPool | None = None

    async def connect(self) -> None:
        """Connect to database and create connection pool."""
        try:
            self.pool = ThreadedConnectionPool(
                minconn=self.config.min_conn,
                maxconn=self.config.max_conn,
                dsn=self.config.dsn,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to create connection pool: {e}") from e

    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            self.pool.closeall()
            self.pool = None

    def get_connection(self) -> Connection:
        """Get connection from pool."""
        if not self.pool:
            raise RuntimeError("Connection pool not initialized. Call connect() first.")
        return self.pool.getconn()  # type: ignore[no-any-return]

    def put_connection(self, conn: Connection) -> None:
        """Return connection to pool."""
        if self.pool:
            self.pool.putconn(conn)
