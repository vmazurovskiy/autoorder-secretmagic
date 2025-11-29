"""Processing history domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class ProcessingRecord:
    """
    Record of a data processing run.

    Tracks when and what data was processed from StarRocks
    for feature engineering purposes.
    """

    client_id: UUID
    table_name: str
    last_ingestion_time: datetime
    records_processed: int = 0
    batch_id: str | None = None
    processed_at: datetime = field(default_factory=datetime.utcnow)
    processing_duration_ms: int | None = None
    status: str = "completed"  # completed, failed, partial
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None  # Set by database

    def is_successful(self) -> bool:
        """Check if processing was successful."""
        return self.status == "completed"

    def is_failed(self) -> bool:
        """Check if processing failed."""
        return self.status == "failed"

    @classmethod
    def create_failed(
        cls,
        client_id: UUID,
        table_name: str,
        last_ingestion_time: datetime,
        error_message: str,
        processing_duration_ms: int | None = None,
    ) -> "ProcessingRecord":
        """Create a failed processing record."""
        return cls(
            client_id=client_id,
            table_name=table_name,
            last_ingestion_time=last_ingestion_time,
            status="failed",
            error_message=error_message,
            processing_duration_ms=processing_duration_ms,
        )
