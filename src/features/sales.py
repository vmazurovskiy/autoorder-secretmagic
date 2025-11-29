"""Sales feature engineering module.

Incremental processing of sales data from StarRocks for ML feature generation.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.database.starrocks import StarRocksClient
from src.domain.client import Client
from src.domain.processing import ProcessingRecord
from src.logger.logger import get_logger
from src.logger.types import Category, param
from src.repository.processing_repository import ProcessingRepository


@dataclass
class SalesProcessingResult:
    """Result of sales data processing."""

    records_fetched: int
    records_processed: int
    last_ingestion_time: datetime
    processing_duration_ms: int
    features_calculated: list[str]
    date_range: tuple[datetime, datetime] | None = None


class SalesFeatureProcessor:
    """
    Processor for sales data feature engineering.

    Reads new sales data from StarRocks incrementally and calculates ML features.
    """

    def __init__(
        self,
        starrocks_client: StarRocksClient,
        processing_repository: ProcessingRepository,
    ) -> None:
        """
        Initialize SalesFeatureProcessor.

        Args:
            starrocks_client: StarRocks client for reading sales data
            processing_repository: Repository for tracking processing history
        """
        self.starrocks = starrocks_client
        self.processing_repo = processing_repository
        self.logger = get_logger().with_category(Category.STARROCKS)

    def get_table_name(self, client: Client) -> str:
        """
        Get sales table name for client.

        Args:
            client: Client with organization_id

        Returns:
            Table name like 'c2_sales'
        """
        return f"c{client.organization_id}_sales"

    def process(self, client: Client) -> SalesProcessingResult:
        """
        Process new sales data for a client.

        Fetches data incrementally based on last_ingestion_time,
        calculates features, and records processing history.

        Args:
            client: Client to process sales for

        Returns:
            SalesProcessingResult with processing details

        Raises:
            Exception: If processing fails
        """
        start_time = time.time()
        table_name = self.get_table_name(client)

        self.logger.info(
            f"Starting sales processing for {client.name}",
            param("client_id", str(client.id)),
            param("table_name", table_name),
        )

        # Get last processed ingestion time
        last_processed = self.processing_repo.get_last_ingestion_time(
            client.id, table_name
        )

        self.logger.debug(
            "Last processed ingestion time",
            param("client_id", str(client.id)),
            param("last_processed", str(last_processed) if last_processed else "None"),
        )

        try:
            # Fetch new records from StarRocks
            new_records, max_ingestion_time = self._fetch_new_records(
                table_name, last_processed
            )

            if not new_records:
                self.logger.info(
                    f"No new sales data for {client.name}",
                    param("client_id", str(client.id)),
                    param("table_name", table_name),
                )
                # Return empty result, don't record if nothing to process
                return SalesProcessingResult(
                    records_fetched=0,
                    records_processed=0,
                    last_ingestion_time=last_processed or datetime.utcnow(),
                    processing_duration_ms=int((time.time() - start_time) * 1000),
                    features_calculated=[],
                )

            # Calculate features from new records
            features_calculated = self._calculate_features(new_records, client)

            processing_duration_ms = int((time.time() - start_time) * 1000)

            # Determine date range from records
            date_range = self._get_date_range(new_records)

            # Record successful processing
            record = ProcessingRecord(
                client_id=client.id,
                table_name=table_name,
                last_ingestion_time=max_ingestion_time,
                records_processed=len(new_records),
                processing_duration_ms=processing_duration_ms,
                status="completed",
                metadata={
                    "features_calculated": features_calculated,
                    "date_range": (
                        [date_range[0].isoformat(), date_range[1].isoformat()]
                        if date_range
                        else None
                    ),
                },
            )
            self.processing_repo.add(record)

            result = SalesProcessingResult(
                records_fetched=len(new_records),
                records_processed=len(new_records),
                last_ingestion_time=max_ingestion_time,
                processing_duration_ms=processing_duration_ms,
                features_calculated=features_calculated,
                date_range=date_range,
            )

            self.logger.info(
                f"Sales processing completed for {client.name}",
                param("client_id", str(client.id)),
                param("records_processed", result.records_processed),
                param("duration_ms", result.processing_duration_ms),
                param("features", features_calculated),
            )

            return result

        except Exception as e:
            processing_duration_ms = int((time.time() - start_time) * 1000)

            # Record failed processing
            failed_record = ProcessingRecord.create_failed(
                client_id=client.id,
                table_name=table_name,
                last_ingestion_time=last_processed or datetime.utcnow(),
                error_message=str(e),
                processing_duration_ms=processing_duration_ms,
            )
            self.processing_repo.add(failed_record)

            self.logger.error(
                f"Sales processing failed for {client.name}",
                e,
                param("client_id", str(client.id)),
                param("table_name", table_name),
            )
            raise

    def _fetch_new_records(
        self,
        table_name: str,
        last_processed: datetime | None,
    ) -> tuple[list[dict[str, Any]], datetime]:
        """
        Fetch new records from StarRocks since last processed time.

        Args:
            table_name: StarRocks table name
            last_processed: Last processed ingestion_time or None

        Returns:
            Tuple of (records list, max ingestion_time)
        """
        if last_processed:
            query = f"""
                SELECT *
                FROM {table_name}
                WHERE ingestion_time > %s
                ORDER BY ingestion_time ASC
            """
            records = self.starrocks.fetch_all(query, (last_processed,))
        else:
            # First time processing - get all records
            # In production, might want to limit to recent period
            query = f"""
                SELECT *
                FROM {table_name}
                ORDER BY ingestion_time ASC
            """
            records = self.starrocks.fetch_all(query)

        if not records:
            return [], last_processed or datetime.utcnow()

        # Get max ingestion_time from fetched records
        max_ingestion_time = max(r["ingestion_time"] for r in records)

        self.logger.debug(
            f"Fetched {len(records)} new records from {table_name}",
            param("table_name", table_name),
            param("records_count", len(records)),
            param("max_ingestion_time", str(max_ingestion_time)),
        )

        return records, max_ingestion_time

    def _calculate_features(
        self,
        records: list[dict[str, Any]],
        client: Client,  # noqa: ARG002 - will be used for feature config
    ) -> list[str]:
        """
        Calculate features from sales records.

        This is a placeholder - actual feature calculation will be implemented
        based on specific ML requirements.

        Args:
            records: Sales records from StarRocks
            client: Client for feature configuration

        Returns:
            List of calculated feature names
        """
        # TODO: Implement actual feature engineering
        # For now, just log what we would calculate

        # Get unique dates and departments
        unique_dates = {r["open_date"] for r in records}
        unique_departments = {r["department_id"] for r in records}
        unique_dishes = {r["dish_id"] for r in records}

        self.logger.debug(
            "Feature calculation input summary",
            param("records", len(records)),
            param("unique_dates", len(unique_dates)),
            param("unique_departments", len(unique_departments)),
            param("unique_dishes", len(unique_dishes)),
        )

        # Placeholder for features that would be calculated
        features = [
            "daily_sales_amount",
            "daily_sales_sum",
            "department_daily_total",
            # Future: rolling averages, seasonality, etc.
        ]

        return features

    def _get_date_range(
        self, records: list[dict[str, Any]]
    ) -> tuple[datetime, datetime] | None:
        """Get min and max open_date from records."""
        if not records:
            return None

        dates = [r["open_date"] for r in records if r.get("open_date")]
        if not dates:
            return None

        return (min(dates), max(dates))
