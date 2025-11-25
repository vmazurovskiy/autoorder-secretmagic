"""Client repository for PostgreSQL."""

import json
from typing import Any
from uuid import UUID

from psycopg2.extras import RealDictCursor

from src.database.postgres import PostgresClient
from src.domain.client import Client
from src.logger.logger import get_logger
from src.logger.types import Category, param


class ClientRepository:
    """Repository for Client CRUD operations in PostgreSQL."""

    def __init__(self, postgres_client: PostgresClient) -> None:
        """
        Initialize ClientRepository.

        Args:
            postgres_client: PostgreSQL client instance
        """
        self.postgres = postgres_client
        self.logger = get_logger().with_category(Category.DATABASE)

    def upsert(self, client: Client) -> None:
        """
        Insert or update client in database.

        Uses PostgreSQL ON CONFLICT DO UPDATE (upsert) for idempotent writes.
        Event Carried State Transfer pattern - полностью заменяем данные клиента.

        Args:
            client: Client to upsert
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO clients (
                        id, name, organization_id, contact_email, contact_phone,
                        status, features_enabled, config_confirmed, config_confirmed_by,
                        config_confirmed_at, source, created_at, updated_at, synced_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        organization_id = EXCLUDED.organization_id,
                        contact_email = EXCLUDED.contact_email,
                        contact_phone = EXCLUDED.contact_phone,
                        status = EXCLUDED.status,
                        features_enabled = EXCLUDED.features_enabled,
                        config_confirmed = EXCLUDED.config_confirmed,
                        config_confirmed_by = EXCLUDED.config_confirmed_by,
                        config_confirmed_at = EXCLUDED.config_confirmed_at,
                        source = EXCLUDED.source,
                        updated_at = EXCLUDED.updated_at,
                        synced_at = EXCLUDED.synced_at
                    """,
                    (
                        str(client.id),
                        client.name,
                        client.organization_id,
                        client.contact_email,
                        client.contact_phone,
                        client.status,
                        json.dumps(client.features_enabled),
                        client.config_confirmed,
                        client.config_confirmed_by,
                        client.config_confirmed_at,
                        client.source,
                        client.created_at,
                        client.updated_at,
                        client.synced_at,
                    ),
                )
                conn.commit()

            self.logger.info(
                f"Client upserted: {client.id}",
                param("client_id", str(client.id)),
                param("client_name", client.name),
            )

        except Exception as e:
            conn.rollback()
            self.logger.error(
                f"Failed to upsert client {client.id}",
                e,
                param("client_id", str(client.id)),
            )
            raise
        finally:
            self.postgres.put_connection(conn)

    def get_by_id(self, client_id: UUID) -> Client | None:
        """
        Get client by ID.

        Args:
            client_id: Client UUID

        Returns:
            Client if found, None otherwise
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, organization_id, contact_email, contact_phone,
                           status, features_enabled, config_confirmed, config_confirmed_by,
                           config_confirmed_at, source, created_at, updated_at, synced_at
                    FROM clients
                    WHERE id = %s
                    """,
                    (str(client_id),),
                )
                row = cur.fetchone()

            if not row:
                return None

            return self._row_to_client(row)

        finally:
            self.postgres.put_connection(conn)

    def get_all_active(self) -> list[Client]:
        """
        Get all active clients.

        Returns:
            List of active clients
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, organization_id, contact_email, contact_phone,
                           status, features_enabled, config_confirmed, config_confirmed_by,
                           config_confirmed_at, source, created_at, updated_at, synced_at
                    FROM clients
                    WHERE status = 'active'
                    ORDER BY name
                    """
                )
                rows = cur.fetchall()

            return [self._row_to_client(row) for row in rows]

        finally:
            self.postgres.put_connection(conn)

    def get_clients_with_feature(self, feature: str) -> list[Client]:
        """
        Get all clients with a specific feature enabled.

        Args:
            feature: Feature name to filter by

        Returns:
            List of clients with the feature enabled
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # JSONB query: features_enabled->>'feature_name' = 'true'
                cur.execute(
                    """
                    SELECT id, name, organization_id, contact_email, contact_phone,
                           status, features_enabled, config_confirmed, config_confirmed_by,
                           config_confirmed_at, source, created_at, updated_at, synced_at
                    FROM clients
                    WHERE status = 'active'
                      AND (features_enabled->>%s)::boolean = true
                    ORDER BY name
                    """,
                    (feature,),
                )
                rows = cur.fetchall()

            return [self._row_to_client(row) for row in rows]

        finally:
            self.postgres.put_connection(conn)

    def _row_to_client(self, row: dict[str, Any]) -> Client:
        """Convert database row to Client domain object."""
        features = row["features_enabled"]
        if isinstance(features, str):
            features = json.loads(features)

        return Client(
            id=UUID(str(row["id"])),
            name=row["name"],
            organization_id=row["organization_id"],
            contact_email=row["contact_email"],
            contact_phone=row["contact_phone"],
            status=row["status"],
            features_enabled=features or {},
            config_confirmed=row["config_confirmed"],
            config_confirmed_by=row["config_confirmed_by"],
            config_confirmed_at=row["config_confirmed_at"],
            source=row["source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            synced_at=row["synced_at"],
        )
