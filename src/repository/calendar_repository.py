"""Calendar repository for StarRocks."""

from datetime import date

import polars as pl

from src.database.starrocks import StarRocksClient
from src.logger.logger import get_logger
from src.logger.types import Category, param


class CalendarRepository:
    """Repository for dim_calendar in StarRocks."""

    TABLE_NAME = "dim_calendar"

    def __init__(self, starrocks_client: StarRocksClient) -> None:
        """
        Initialize CalendarRepository.

        Args:
            starrocks_client: StarRocks client instance
        """
        self.starrocks = starrocks_client
        self.logger = get_logger().with_category(Category.STARROCKS)

    def get_date_range(self) -> tuple[date | None, date | None]:
        """
        Get min and max dates in dim_calendar.

        Returns:
            Tuple (min_date, max_date), both None if table is empty
        """
        result = self.starrocks.fetch_one(
            f"SELECT MIN(`date`) as min_date, MAX(`date`) as max_date FROM {self.TABLE_NAME}"
        )

        if result is None:
            return None, None

        return result.get("min_date"), result.get("max_date")

    def get_max_date(self) -> date | None:
        """
        Get maximum date in dim_calendar.

        Returns:
            Maximum date or None if table is empty
        """
        _, max_date = self.get_date_range()
        return max_date

    def count(self) -> int:
        """
        Get total number of rows in dim_calendar.

        Returns:
            Row count
        """
        result = self.starrocks.fetch_one(
            f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME}"
        )
        return result["cnt"] if result else 0

    def exists(self) -> bool:
        """
        Check if dim_calendar table exists and has data.

        Returns:
            True if table exists and has data
        """
        try:
            return self.count() > 0
        except Exception:
            return False

    def truncate(self) -> None:
        """Truncate dim_calendar table."""
        self.starrocks.execute(f"TRUNCATE TABLE {self.TABLE_NAME}")
        self.logger.info("dim_calendar truncated")

    def insert_dataframe(self, df: pl.DataFrame) -> int:
        """
        Insert Polars DataFrame into dim_calendar.

        Uses batch INSERT for efficiency.
        StarRocks supports INSERT INTO ... VALUES syntax.

        Args:
            df: Polars DataFrame with calendar data

        Returns:
            Number of rows inserted
        """
        if df.is_empty():
            return 0

        # Get column names from DataFrame
        columns = df.columns

        # Build INSERT statement
        placeholders = ", ".join(["%s"] * len(columns))
        columns_str = ", ".join([f"`{c}`" for c in columns])
        insert_sql = f"INSERT INTO {self.TABLE_NAME} ({columns_str}) VALUES ({placeholders})"

        # Convert DataFrame to list of tuples
        rows = df.rows()

        # Insert in batches (StarRocks handles large batches well)
        batch_size = 1000
        total_inserted = 0

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            with self.starrocks.cursor() as cursor:
                cursor.executemany(insert_sql, batch)
                total_inserted += len(batch)

        self.logger.info(
            "Inserted rows into dim_calendar",
            param("rows", total_inserted),
        )

        return total_inserted

    def upsert_dataframe(self, df: pl.DataFrame) -> int:
        """
        Upsert Polars DataFrame into dim_calendar.

        Deletes existing dates and inserts new data.
        StarRocks DUPLICATE KEY model allows this pattern.

        Args:
            df: Polars DataFrame with calendar data

        Returns:
            Number of rows inserted
        """
        if df.is_empty():
            return 0

        # Get date range from DataFrame
        min_date = df.select(pl.col("date").min()).item()
        max_date = df.select(pl.col("date").max()).item()

        # Delete existing data in range
        self.starrocks.execute(
            f"DELETE FROM {self.TABLE_NAME} WHERE `date` >= %s AND `date` <= %s",
            (min_date, max_date),
        )

        self.logger.info(
            "Deleted existing dates from dim_calendar",
            param("from", str(min_date)),
            param("to", str(max_date)),
        )

        # Insert new data
        return self.insert_dataframe(df)

    def get_for_dates(self, dates: list[date]) -> pl.DataFrame:
        """
        Get calendar data for specific dates.

        Args:
            dates: List of dates to fetch

        Returns:
            Polars DataFrame with calendar data
        """
        if not dates:
            return pl.DataFrame()

        placeholders = ", ".join(["%s"] * len(dates))
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE `date` IN ({placeholders}) ORDER BY `date`"

        results = self.starrocks.fetch_all(query, tuple(dates))
        return pl.DataFrame(results) if results else pl.DataFrame()

    def get_range(self, date_from: date, date_to: date) -> pl.DataFrame:
        """
        Get calendar data for date range.

        Args:
            date_from: Start date (inclusive)
            date_to: End date (inclusive)

        Returns:
            Polars DataFrame with calendar data
        """
        query = f"""
            SELECT * FROM {self.TABLE_NAME}
            WHERE `date` >= %s AND `date` <= %s
            ORDER BY `date`
        """

        results = self.starrocks.fetch_all(query, (date_from, date_to))
        return pl.DataFrame(results) if results else pl.DataFrame()

    def ensure_table_exists(self) -> bool:
        """
        Check if dim_calendar table exists, create if not.

        Returns:
            True if table exists or was created
        """
        try:
            # Check if table exists
            result = self.starrocks.fetch_one(
                "SHOW TABLES LIKE %s", (self.TABLE_NAME,)
            )
            if result:
                return True

            # Table doesn't exist - log warning
            # Table should be created by init script
            self.logger.warn(
                f"Table {self.TABLE_NAME} does not exist. "
                "Run scripts/starrocks/init/001_dim_calendar.sql"
            )
            return False

        except Exception as e:
            self.logger.error(
                "Failed to check dim_calendar table",
                param("error", str(e)),
            )
            return False
