"""Calendar dimension module for feature engineering.

Generates dim_calendar table with holidays, weekends, and ML features.
Common reference for all clients, used for:
- Calendar feature calculation
- Sparse to dense time series transformation

Total: ~55 columns including:
- Base components (date, iso_week, month, etc.)
- Sin/cos cyclic features for neural networks
- Binary day-of-week flags
- Official holidays from isdayoff.ru
- Russian holiday flags (hardcoded)
- Salary/business cycle features
"""

import math
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import httpx
import polars as pl

from src.logger.logger import get_logger
from src.logger.types import Category, param


@dataclass
class CalendarConfig:
    """Configuration for calendar generation."""

    region: str = "ru"
    start_date: date = field(default_factory=lambda: date(2020, 1, 1))
    future_upload_day: int = 10  # Day of month
    future_upload_month: int = 12  # Month (December)


class CalendarBuilder:
    """
    Builder for dim_calendar reference table.

    Generates calendar with ~55 columns:
    - Base date components
    - Sin/cos cyclic transforms
    - Binary weekday flags
    - Official holidays (isdayoff.ru + python-holidays)
    - Holiday block features
    - Russian holiday flags
    - Salary/business cycle features
    """

    def __init__(self, config: CalendarConfig | None = None) -> None:
        self.config = config or CalendarConfig()
        self.logger = get_logger().with_category(Category.STARROCKS)

    def build(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> pl.DataFrame:
        """
        Build dim_calendar DataFrame with all features.

        Args:
            date_from: Start date. Defaults to config.start_date.
            date_to: End date. Defaults to end of current year.

        Returns:
            Polars DataFrame with ~55 calendar columns.
        """
        start_time = time.time()

        # Determine date range
        date_from = date_from or self.config.start_date
        if date_to is None:
            today = datetime.utcnow().date()
            date_to = date(today.year, 12, 31)

        self.logger.info(
            "Building dim_calendar",
            param("date_from", str(date_from)),
            param("date_to", str(date_to)),
            param("region", self.config.region),
        )

        # 1. Base date spine
        cal = self._build_date_spine(date_from, date_to)

        # 2. Base components
        cal = self._add_base_components(cal)

        # 3. Sin/cos cyclic features
        cal = self._add_cyclic_features(cal)

        # 4. Binary weekday flags
        cal = self._add_weekday_flags(cal)

        # 5. Official holidays from isdayoff.ru
        cal = self._apply_isdayoff(cal)

        # 6. Holidays from python-holidays (fallback)
        cal = self._apply_python_holidays(cal)

        # 7. Holiday block features
        cal = self._add_holiday_block_features(cal)

        # 8. Russian holiday flags (hardcoded)
        cal = self._add_russian_holidays(cal)

        # 9. Salary/business cycle features
        cal = self._add_business_cycle_features(cal)

        # 10. Seasons
        cal = self._add_seasons(cal)

        duration_ms = int((time.time() - start_time) * 1000)

        self.logger.info(
            "dim_calendar built successfully",
            param("total_days", cal.height),
            param("columns", len(cal.columns)),
            param("duration_ms", duration_ms),
        )

        return cal

    def should_update(self, current_max_date: date | None) -> tuple[bool, date | None]:
        """
        Check if calendar needs update based on config rules.

        Args:
            current_max_date: Maximum date in existing dim_calendar (None if empty).

        Returns:
            Tuple of (needs_update, new_date_to).
        """
        today = datetime.utcnow().date()
        current_year = today.year

        # If empty - need full load
        if current_max_date is None:
            return True, date(current_year, 12, 31)

        # Check if we need to load next year
        upload_trigger = date(
            current_year,
            self.config.future_upload_month,
            self.config.future_upload_day,
        )

        next_year_end = date(current_year + 1, 12, 31)

        if today >= upload_trigger and current_max_date < next_year_end:
            return True, next_year_end

        # Check if current year is not fully covered
        current_year_end = date(current_year, 12, 31)
        if current_max_date < current_year_end:
            return True, current_year_end

        return False, None

    def _build_date_spine(self, date_from: date, date_to: date) -> pl.DataFrame:
        """Generate continuous date range."""
        dates = pl.date_range(
            start=date_from,
            end=date_to,
            interval="1d",
            eager=True,
        )
        return pl.DataFrame({"date": dates})

    def _add_base_components(self, cal: pl.DataFrame) -> pl.DataFrame:
        """Add base date components."""
        return cal.with_columns([
            # ISO components
            pl.col("date").dt.iso_year().alias("iso_year"),
            pl.col("date").dt.week().alias("iso_week"),
            pl.col("date").dt.weekday().add(1).alias("iso_dow"),  # 1=Mon...7=Sun
            # Gregorian components
            pl.col("date").dt.year().alias("year"),
            pl.col("date").dt.month().alias("month"),
            pl.col("date").dt.day().alias("day"),
            pl.col("date").dt.quarter().alias("quarter"),
            pl.col("date").dt.ordinal_day().alias("day_of_year"),
            # Weekend flag
            pl.col("date").dt.weekday().add(1).is_in([6, 7]).alias("is_weekend_iso"),
        ])

    def _add_cyclic_features(self, cal: pl.DataFrame) -> pl.DataFrame:
        """Add sin/cos cyclic features for neural networks."""
        pi2 = 2 * math.pi

        return cal.with_columns([
            # Day of week (period=7)
            (pi2 * pl.col("iso_dow") / 7.0).sin().alias("dow_sin"),
            (pi2 * pl.col("iso_dow") / 7.0).cos().alias("dow_cos"),
            # Week of year (period=53)
            (pi2 * pl.col("iso_week") / 53.0).sin().alias("week_sin"),
            (pi2 * pl.col("iso_week") / 53.0).cos().alias("week_cos"),
            # Day of year (period=366)
            (pi2 * pl.col("day_of_year") / 366.0).sin().alias("doy_sin"),
            (pi2 * pl.col("day_of_year") / 366.0).cos().alias("doy_cos"),
            # Day of month (dynamic period based on month length)
            (pi2 * pl.col("day") / pl.col("date").dt.month_end().dt.day()).sin().alias("day_sin"),
            (pi2 * pl.col("day") / pl.col("date").dt.month_end().dt.day()).cos().alias("day_cos"),
            # Month (period=12)
            (pi2 * pl.col("month") / 12.0).sin().alias("month_sin"),
            (pi2 * pl.col("month") / 12.0).cos().alias("month_cos"),
        ])

    def _add_weekday_flags(self, cal: pl.DataFrame) -> pl.DataFrame:
        """Add binary flags for each day of week."""
        return cal.with_columns([
            (pl.col("iso_dow") == 1).cast(pl.Int8).alias("is_monday"),
            (pl.col("iso_dow") == 2).cast(pl.Int8).alias("is_tuesday"),
            (pl.col("iso_dow") == 3).cast(pl.Int8).alias("is_wednesday"),
            (pl.col("iso_dow") == 4).cast(pl.Int8).alias("is_thursday"),
            (pl.col("iso_dow") == 5).cast(pl.Int8).alias("is_friday"),
            (pl.col("iso_dow") == 6).cast(pl.Int8).alias("is_saturday"),
            (pl.col("iso_dow") == 7).cast(pl.Int8).alias("is_sunday"),
        ])

    def _apply_isdayoff(self, cal: pl.DataFrame) -> pl.DataFrame:
        """Apply official day-off data from isdayoff.ru API."""
        # Initialize columns
        cal = cal.with_columns([
            pl.lit(False).alias("is_day_off_official"),
            pl.lit(False).alias("is_preholiday_official"),
        ])

        years = cal.select("year").unique().to_series().to_list()
        all_codes: list[dict[str, Any]] = []

        for year in sorted(years):
            try:
                codes = self._fetch_isdayoff_year(int(year))
                all_codes.extend(codes)
            except Exception as e:
                self.logger.warn(
                    f"Failed to fetch isdayoff for year {year}",
                    param("error", str(e)),
                )

        if not all_codes:
            self.logger.warn("No isdayoff data fetched, using ISO weekends only")
            return cal.with_columns([
                pl.col("is_weekend_iso").alias("is_day_off_official"),
            ])

        codes_df = pl.DataFrame(all_codes).with_columns(
            pl.col("date").cast(pl.Date)
        )

        # Join and update flags
        cal = cal.join(codes_df, on="date", how="left")

        cal = cal.with_columns([
            pl.when(pl.col("code") == "1")
            .then(pl.lit(True))
            .otherwise(pl.lit(False))
            .alias("is_day_off_official"),
            pl.when(pl.col("code") == "2")
            .then(pl.lit(True))
            .otherwise(pl.lit(False))
            .alias("is_preholiday_official"),
        ])

        # Official weekend = day_off AND iso_weekend
        cal = cal.with_columns(
            (pl.col("is_day_off_official") & pl.col("is_weekend_iso"))
            .alias("is_weekend_official")
        )

        return cal.drop("code")

    def _fetch_isdayoff_year(self, year: int) -> list[dict[str, Any]]:
        """Fetch day-off codes from isdayoff.ru for a year."""
        url = f"https://isdayoff.ru/api/getdata?year={year}&cc={self.config.region}&pre=1&delimeter=%0A"

        for attempt in range(3):
            try:
                with httpx.Client(timeout=20.0) as client:
                    resp = client.get(url)
                    resp.raise_for_status()

                lines = [ln.strip() for ln in resp.text.splitlines() if ln.strip()]

                # Parse response
                if len(lines) == 1 and set(lines[0]) <= set("0124"):
                    codes = list(lines[0])
                else:
                    codes = lines

                # Generate dates
                start = date(year, 1, 1)
                end = date(year, 12, 31)
                days = (end - start).days + 1

                # Pad or truncate
                if len(codes) < days:
                    codes = codes + ["0"] * (days - len(codes))
                elif len(codes) > days:
                    codes = codes[:days]

                result = []
                current = start
                for code in codes:
                    result.append({"date": current, "code": code})
                    current += timedelta(days=1)

                self.logger.debug(
                    f"Fetched isdayoff for {year}",
                    param("days", len(result)),
                )
                return result

            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)

        return []

    def _apply_python_holidays(self, cal: pl.DataFrame) -> pl.DataFrame:
        """Apply holiday dates from python-holidays library."""
        try:
            import holidays
        except ImportError:
            self.logger.warn("python-holidays not installed")
            return cal.with_columns(pl.lit(False).alias("is_holiday_official"))

        years = cal.select("year").unique().to_series().to_list()
        try:
            hol = holidays.country_holidays(
                self.config.region.upper(),
                years=sorted(int(y) for y in years),
            )
        except Exception as e:
            self.logger.warn(f"Failed to get holidays: {e}")
            return cal.with_columns(pl.lit(False).alias("is_holiday_official"))

        holiday_dates = set(hol.keys())

        return cal.with_columns(
            pl.col("date")
            .map_elements(lambda d: d in holiday_dates, return_dtype=pl.Boolean)
            .alias("is_holiday_official")
        )

    def _add_holiday_block_features(self, cal: pl.DataFrame) -> pl.DataFrame:
        """Add holiday block detection and transition features."""
        cal = cal.sort("date")

        # Get holiday series
        h = cal.select("is_holiday_official").to_series().fill_null(False)
        h_prev = h.shift(1).fill_null(False)
        h_next = h.shift(-1).fill_null(False)  # noqa: F841

        # Block start/end detection
        block_start = h & ~h_prev

        # Group ID for blocks
        group_changes = (h != h_prev).cast(pl.Int64)
        group_id = group_changes.cum_sum()

        # Position within block
        positions = []
        current_pos = 0
        prev_group = None
        for is_hol, grp in zip(h.to_list(), group_id.to_list(), strict=True):
            if is_hol:
                if grp != prev_group:
                    current_pos = 0
                positions.append(current_pos)
                current_pos += 1
            else:
                positions.append(None)
            prev_group = grp

        block_pos = pl.Series("holiday_block_pos", positions, dtype=pl.Int32)

        # Pre-holiday start
        preholiday_start = block_start.shift(-1).fill_null(False)

        # Day-off transitions
        day_off = cal.select("is_day_off_official").to_series().fill_null(False)
        day_off_prev = day_off.shift(1).fill_null(False)
        day_off_next = day_off.shift(-1).fill_null(False)

        # Weekend transitions
        weekend_iso = cal.select("is_weekend_iso").to_series()
        weekend_iso_next = weekend_iso.shift(-1).fill_null(False)
        weekend_official = cal.select("is_weekend_official").to_series()

        return cal.with_columns([
            h.alias("within_holiday_block"),
            block_pos,
            preholiday_start.alias("is_preholiday_start"),
            (preholiday_start & ~day_off).alias("is_preholiday_start_working"),
            (day_off & ~day_off_next).alias("is_last_off_before_work"),
            (~day_off & day_off_prev).alias("is_first_work_after_off"),
            (weekend_iso & ~weekend_iso_next).alias("is_last_weekend_iso_before_work"),
            (weekend_official & ~day_off_next).alias("is_last_official_weekend_before_work"),
            (pl.col("iso_dow") == 5).alias("is_pre_weekend_iso"),
            day_off_next.alias("is_pre_weekend_official"),
            (weekend_iso & ~day_off).alias("is_working_weekend"),
            (~weekend_iso & day_off).alias("is_day_off_non_weekend"),
        ])

    def _add_russian_holidays(self, cal: pl.DataFrame) -> pl.DataFrame:
        """Add hardcoded Russian holiday flags."""
        return cal.with_columns([
            # New Year holidays (Jan 1-8)
            ((pl.col("month") == 1) & (pl.col("day") <= 8))
            .cast(pl.Int8).alias("is_new_year_holidays"),
            # Defender of the Fatherland Day (Feb 23)
            ((pl.col("month") == 2) & (pl.col("day") == 23))
            .cast(pl.Int8).alias("is_defender_day"),
            # International Women's Day (Mar 8)
            ((pl.col("month") == 3) & (pl.col("day") == 8))
            .cast(pl.Int8).alias("is_womens_day"),
            # Spring and Labour Day (May 1)
            ((pl.col("month") == 5) & (pl.col("day") == 1))
            .cast(pl.Int8).alias("is_labour_day"),
            # Victory Day (May 9)
            ((pl.col("month") == 5) & (pl.col("day") == 9))
            .cast(pl.Int8).alias("is_victory_day"),
            # Russia Day (Jun 12)
            ((pl.col("month") == 6) & (pl.col("day") == 12))
            .cast(pl.Int8).alias("is_russia_day"),
            # Unity Day (Nov 4)
            ((pl.col("month") == 11) & (pl.col("day") == 4))
            .cast(pl.Int8).alias("is_unity_day"),
            # Orthodox Christmas (Jan 7)
            ((pl.col("month") == 1) & (pl.col("day") == 7))
            .cast(pl.Int8).alias("is_orthodox_christmas"),
        ])

    def _add_business_cycle_features(self, cal: pl.DataFrame) -> pl.DataFrame:
        """Add salary and business cycle features."""
        return cal.with_columns([
            # End of month (last 3 days)
            (pl.col("day") >= pl.col("date").dt.month_end().dt.day() - 2)
            .cast(pl.Int8).alias("is_end_of_month"),
            # Days since month start normalized (0.0-1.0)
            (pl.col("day") / pl.col("date").dt.month_end().dt.day())
            .alias("days_since_month_start_norm"),
            # Quarter end (last 7 days of quarter)
            pl.when(
                ((pl.col("month") == 3) & (pl.col("day") >= 25)) |
                ((pl.col("month") == 6) & (pl.col("day") >= 24)) |
                ((pl.col("month") == 9) & (pl.col("day") >= 24)) |
                ((pl.col("month") == 12) & (pl.col("day") >= 25))
            ).then(1).otherwise(0).cast(pl.Int8).alias("is_quarter_end"),
        ])

    def _add_seasons(self, cal: pl.DataFrame) -> pl.DataFrame:
        """Add meteorological and ISO seasons."""
        return cal.with_columns([
            # Meteorological season
            pl.when(pl.col("month").is_in([12, 1, 2]))
            .then(pl.lit("DJF"))
            .when(pl.col("month").is_in([3, 4, 5]))
            .then(pl.lit("MAM"))
            .when(pl.col("month").is_in([6, 7, 8]))
            .then(pl.lit("JJA"))
            .otherwise(pl.lit("SON"))
            .alias("season_meteo"),
            # ISO season with year
            pl.concat_str([
                pl.when(pl.col("month").is_in([12, 1, 2]))
                .then(pl.lit("DJF"))
                .when(pl.col("month").is_in([3, 4, 5]))
                .then(pl.lit("MAM"))
                .when(pl.col("month").is_in([6, 7, 8]))
                .then(pl.lit("JJA"))
                .otherwise(pl.lit("SON")),
                pl.lit("-"),
                pl.col("iso_year").cast(pl.Utf8),
            ]).alias("season_iso"),
        ])

    def get_column_list(self) -> list[str]:
        """Get ordered list of all dim_calendar columns."""
        return [
            # Base components (9)
            "date", "iso_year", "iso_week", "iso_dow",
            "year", "month", "day", "quarter", "day_of_year",
            # Cyclic features (10)
            "dow_sin", "dow_cos", "week_sin", "week_cos",
            "doy_sin", "doy_cos", "day_sin", "day_cos",
            "month_sin", "month_cos",
            # Weekday flags (7)
            "is_monday", "is_tuesday", "is_wednesday", "is_thursday",
            "is_friday", "is_saturday", "is_sunday",
            # Weekend/holiday flags (5)
            "is_weekend_iso", "is_day_off_official", "is_weekend_official",
            "is_holiday_official", "is_preholiday_official",
            # Holiday block features (4)
            "within_holiday_block", "holiday_block_pos",
            "is_preholiday_start", "is_preholiday_start_working",
            # Transition features (8)
            "is_last_off_before_work", "is_first_work_after_off",
            "is_last_weekend_iso_before_work", "is_last_official_weekend_before_work",
            "is_pre_weekend_iso", "is_pre_weekend_official",
            "is_working_weekend", "is_day_off_non_weekend",
            # Russian holidays (8)
            "is_new_year_holidays", "is_defender_day", "is_womens_day",
            "is_labour_day", "is_victory_day", "is_russia_day",
            "is_unity_day", "is_orthodox_christmas",
            # Business cycles (3)
            "is_end_of_month", "days_since_month_start_norm", "is_quarter_end",
            # Seasons (2)
            "season_meteo", "season_iso",
        ]
