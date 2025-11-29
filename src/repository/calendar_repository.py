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

            # Table doesn't exist - create it
            self.logger.info(f"Table {self.TABLE_NAME} does not exist, creating...")
            self._create_table()
            self.logger.info(f"Table {self.TABLE_NAME} created successfully")
            return True

        except Exception as e:
            self.logger.error(
                "Failed to ensure dim_calendar table exists",
                e,
            )
            return False

    def _create_table(self) -> None:
        """Create dim_calendar table in StarRocks."""
        # StarRocks DUPLICATE KEY model does not support DEFAULT values
        # All values must be explicitly provided during INSERT
        ddl = """
        CREATE TABLE IF NOT EXISTS dim_calendar (
            `date` DATE NOT NULL COMMENT 'Календарная дата',
            iso_year INT NOT NULL COMMENT 'ISO год (год ISO-недели)',
            iso_week INT NOT NULL COMMENT 'ISO неделя (1-53)',
            iso_dow TINYINT NOT NULL COMMENT 'ISO день недели: 1=Пн...7=Вс',
            `year` INT NOT NULL COMMENT 'Григорианский год',
            `month` TINYINT NOT NULL COMMENT 'Месяц (1-12)',
            `day` TINYINT NOT NULL COMMENT 'День месяца (1-31)',
            `quarter` TINYINT NOT NULL COMMENT 'Квартал (1-4)',
            day_of_year SMALLINT NOT NULL COMMENT 'День года (1-366)',
            dow_sin DOUBLE NOT NULL COMMENT 'sin(2π * iso_dow / 7)',
            dow_cos DOUBLE NOT NULL COMMENT 'cos(2π * iso_dow / 7)',
            week_sin DOUBLE NOT NULL COMMENT 'sin(2π * iso_week / 53)',
            week_cos DOUBLE NOT NULL COMMENT 'cos(2π * iso_week / 53)',
            doy_sin DOUBLE NOT NULL COMMENT 'sin(2π * day_of_year / 366)',
            doy_cos DOUBLE NOT NULL COMMENT 'cos(2π * day_of_year / 366)',
            day_sin DOUBLE NOT NULL COMMENT 'sin(2π * day / days_in_month)',
            day_cos DOUBLE NOT NULL COMMENT 'cos(2π * day / days_in_month)',
            month_sin DOUBLE NOT NULL COMMENT 'sin(2π * month / 12)',
            month_cos DOUBLE NOT NULL COMMENT 'cos(2π * month / 12)',
            is_monday TINYINT NOT NULL COMMENT 'Понедельник',
            is_tuesday TINYINT NOT NULL COMMENT 'Вторник',
            is_wednesday TINYINT NOT NULL COMMENT 'Среда',
            is_thursday TINYINT NOT NULL COMMENT 'Четверг',
            is_friday TINYINT NOT NULL COMMENT 'Пятница',
            is_saturday TINYINT NOT NULL COMMENT 'Суббота',
            is_sunday TINYINT NOT NULL COMMENT 'Воскресенье',
            is_weekend_iso BOOLEAN NOT NULL COMMENT 'Суббота/воскресенье по ISO',
            is_day_off_official BOOLEAN NOT NULL COMMENT 'Официальный нерабочий день',
            is_weekend_official BOOLEAN NOT NULL COMMENT 'Официальный выходной',
            is_holiday_official BOOLEAN NOT NULL COMMENT 'Официальный праздник',
            is_preholiday_official BOOLEAN NOT NULL COMMENT 'Сокращённый рабочий день',
            within_holiday_block BOOLEAN NOT NULL COMMENT 'День внутри праздничного блока',
            holiday_block_pos INT NULL COMMENT 'Позиция в блоке (0-indexed)',
            is_preholiday_start BOOLEAN NOT NULL COMMENT 'День перед праздничным блоком',
            is_preholiday_start_working BOOLEAN NOT NULL COMMENT 'Рабочий день перед праздничным блоком',
            is_last_off_before_work BOOLEAN NOT NULL COMMENT 'Последний нерабочий перед рабочим',
            is_first_work_after_off BOOLEAN NOT NULL COMMENT 'Первый рабочий после нерабочих',
            is_last_weekend_iso_before_work BOOLEAN NOT NULL COMMENT 'Последний ISO выходной перед работой',
            is_last_official_weekend_before_work BOOLEAN NOT NULL COMMENT 'Последний официальный выходной перед работой',
            is_pre_weekend_iso BOOLEAN NOT NULL COMMENT 'Пятница (канун ISO-выходных)',
            is_pre_weekend_official BOOLEAN NOT NULL COMMENT 'Завтра официальный нерабочий',
            is_working_weekend BOOLEAN NOT NULL COMMENT 'ISO выходной, но рабочий день',
            is_day_off_non_weekend BOOLEAN NOT NULL COMMENT 'Будний, но нерабочий',
            is_new_year_holidays TINYINT NOT NULL COMMENT 'Новогодние каникулы (1-8 января)',
            is_defender_day TINYINT NOT NULL COMMENT 'День защитника Отечества (23 февраля)',
            is_womens_day TINYINT NOT NULL COMMENT 'Международный женский день (8 марта)',
            is_labour_day TINYINT NOT NULL COMMENT 'Праздник Весны и Труда (1 мая)',
            is_victory_day TINYINT NOT NULL COMMENT 'День Победы (9 мая)',
            is_russia_day TINYINT NOT NULL COMMENT 'День России (12 июня)',
            is_unity_day TINYINT NOT NULL COMMENT 'День народного единства (4 ноября)',
            is_orthodox_christmas TINYINT NOT NULL COMMENT 'Рождество Христово (7 января)',
            is_end_of_month TINYINT NOT NULL COMMENT 'Последние 3 дня месяца',
            days_since_month_start_norm DOUBLE NOT NULL COMMENT 'Дни от начала месяца (0.0-1.0)',
            is_quarter_end TINYINT NOT NULL COMMENT 'Последние 7 дней квартала',
            season_meteo VARCHAR(3) NOT NULL COMMENT 'Метеосезон: DJF/MAM/JJA/SON',
            season_iso VARCHAR(10) NOT NULL COMMENT 'Сезон с ISO-годом'
        )
        ENGINE = OLAP
        DUPLICATE KEY(`date`)
        COMMENT 'Календарный справочник для feature engineering (~55 колонок)'
        DISTRIBUTED BY HASH(`date`) BUCKETS 1
        PROPERTIES (
            "replication_num" = "1",
            "in_memory" = "true"
        )
        """
        self.starrocks.execute(ddl)
