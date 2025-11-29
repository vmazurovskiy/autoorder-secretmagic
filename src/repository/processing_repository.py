"""Processing history repository for PostgreSQL."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg2.extras import RealDictCursor

from src.database.postgres import PostgresClient
from src.domain.processing import ProcessingRecord
from src.logger.logger import get_logger
from src.logger.types import Category, param


class ProcessingRepository:
    """Repository for ProcessingRecord CRUD operations in PostgreSQL."""

    def __init__(self, postgres_client: PostgresClient) -> None:
        """
        Initialize ProcessingRepository.

        Args:
            postgres_client: PostgreSQL client instance
        """
        self.postgres = postgres_client
        self.logger = get_logger().with_category(Category.DATABASE)

    def add(self, record: ProcessingRecord) -> int:
        """
        Add new processing record to history.

        Args:
            record: ProcessingRecord to save

        Returns:
            ID of inserted record
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO processing_history (
                        client_id, table_name, last_ingestion_time,
                        records_processed, batch_id, processed_at,
                        processing_duration_ms, status, error_message, metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id
                    """,
                    (
                        str(record.client_id),
                        record.table_name,
                        record.last_ingestion_time,
                        record.records_processed,
                        record.batch_id,
                        record.processed_at,
                        record.processing_duration_ms,
                        record.status,
                        record.error_message,
                        json.dumps(record.metadata),
                    ),
                )
                record_id = cur.fetchone()[0]
                conn.commit()

            self.logger.info(
                f"Processing record added: {record.table_name}",
                param("record_id", record_id),
                param("client_id", str(record.client_id)),
                param("table_name", record.table_name),
                param("status", record.status),
                param("records_processed", record.records_processed),
            )
            return record_id

        except Exception as e:
            conn.rollback()
            self.logger.error(
                f"Failed to add processing record for {record.table_name}",
                e,
                param("client_id", str(record.client_id)),
            )
            raise
        finally:
            self.postgres.put_connection(conn)

    def get_last_successful(
        self, client_id: UUID, table_name: str
    ) -> ProcessingRecord | None:
        """
        Get the last successful processing record for client and table.

        Args:
            client_id: Client UUID
            table_name: Table name (e.g., 'c2_sales')

        Returns:
            Last successful ProcessingRecord or None if never processed
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, client_id, table_name, last_ingestion_time,
                           records_processed, batch_id, processed_at,
                           processing_duration_ms, status, error_message, metadata
                    FROM processing_history
                    WHERE client_id = %s
                      AND table_name = %s
                      AND status = 'completed'
                    ORDER BY processed_at DESC
                    LIMIT 1
                    """,
                    (str(client_id), table_name),
                )
                row = cur.fetchone()

            if not row:
                return None

            return self._row_to_record(row)

        finally:
            self.postgres.put_connection(conn)

    def get_last_ingestion_time(
        self, client_id: UUID, table_name: str
    ) -> datetime | None:
        """
        Get the last successfully processed ingestion_time for client and table.

        Shortcut method for incremental processing.

        Args:
            client_id: Client UUID
            table_name: Table name (e.g., 'c2_sales')

        Returns:
            Last processed ingestion_time or None if never processed
        """
        record = self.get_last_successful(client_id, table_name)
        return record.last_ingestion_time if record else None

    def get_history(
        self,
        client_id: UUID,
        table_name: str | None = None,
        limit: int = 10,
    ) -> list[ProcessingRecord]:
        """
        Get processing history for a client.

        Args:
            client_id: Client UUID
            table_name: Optional table name filter
            limit: Maximum records to return

        Returns:
            List of ProcessingRecords, most recent first
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if table_name:
                    cur.execute(
                        """
                        SELECT id, client_id, table_name, last_ingestion_time,
                               records_processed, batch_id, processed_at,
                               processing_duration_ms, status, error_message, metadata
                        FROM processing_history
                        WHERE client_id = %s AND table_name = %s
                        ORDER BY processed_at DESC
                        LIMIT %s
                        """,
                        (str(client_id), table_name, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, client_id, table_name, last_ingestion_time,
                               records_processed, batch_id, processed_at,
                               processing_duration_ms, status, error_message, metadata
                        FROM processing_history
                        WHERE client_id = %s
                        ORDER BY processed_at DESC
                        LIMIT %s
                        """,
                        (str(client_id), limit),
                    )
                rows = cur.fetchall()

            return [self._row_to_record(row) for row in rows]

        finally:
            self.postgres.put_connection(conn)

    def get_failed_records(self, limit: int = 100) -> list[ProcessingRecord]:
        """
        Get recent failed processing records for monitoring.

        Args:
            limit: Maximum records to return

        Returns:
            List of failed ProcessingRecords
        """
        conn = self.postgres.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, client_id, table_name, last_ingestion_time,
                           records_processed, batch_id, processed_at,
                           processing_duration_ms, status, error_message, metadata
                    FROM processing_history
                    WHERE status = 'failed'
                    ORDER BY processed_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()

            return [self._row_to_record(row) for row in rows]

        finally:
            self.postgres.put_connection(conn)

    def _row_to_record(self, row: dict[str, Any]) -> ProcessingRecord:
        """Convert database row to ProcessingRecord domain object."""
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return ProcessingRecord(
            id=row["id"],
            client_id=UUID(str(row["client_id"])),
            table_name=row["table_name"],
            last_ingestion_time=row["last_ingestion_time"],
            records_processed=row["records_processed"],
            batch_id=row["batch_id"],
            processed_at=row["processed_at"],
            processing_duration_ms=row["processing_duration_ms"],
            status=row["status"],
            error_message=row["error_message"],
            metadata=metadata or {},
        )
