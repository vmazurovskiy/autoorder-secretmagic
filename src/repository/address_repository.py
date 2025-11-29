"""Address repository for StarRocks."""

from datetime import datetime

from src.database.starrocks import StarRocksClient
from src.domain.geocode import DimAddress
from src.logger.logger import get_logger
from src.logger.types import Category, param


class AddressRepository:
    """
    Repository для dim_address в StarRocks.

    Хранит кэш геокодирования адресов с координатами
    для точного адреса, города и района.
    """

    TABLE_NAME = "dim_address"

    def __init__(self, starrocks_client: StarRocksClient) -> None:
        """
        Initialize AddressRepository.

        Args:
            starrocks_client: StarRocks client instance
        """
        self.starrocks = starrocks_client
        self.logger = get_logger().with_category(Category.STARROCKS)

    def get_by_raw_address(self, raw_address: str) -> DimAddress | None:
        """
        Найти адрес в кэше по сырому адресу.

        Args:
            raw_address: Сырой адрес для поиска

        Returns:
            DimAddress если найден, None если нет в кэше
        """
        result = self.starrocks.fetch_one(
            f"""
            SELECT raw_address, normalized_address, lat, lon, address_status, geocode_kind,
                   country, province, locality, district, street, house,
                   locality_lat, locality_lon, locality_status,
                   district_lat, district_lon, district_status,
                   error_message, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE raw_address = %s
            """,
            (raw_address,),
        )

        if not result:
            return None

        return DimAddress.from_db_row(result)

    def get_by_raw_addresses(self, raw_addresses: list[str]) -> dict[str, DimAddress]:
        """
        Найти адреса в кэше (batch).

        Args:
            raw_addresses: Список сырых адресов

        Returns:
            Dict {raw_address: DimAddress} для найденных адресов
        """
        if not raw_addresses:
            return {}

        # Строим IN clause с placeholders
        placeholders = ", ".join(["%s"] * len(raw_addresses))
        results = self.starrocks.fetch_all(
            f"""
            SELECT raw_address, normalized_address, lat, lon, address_status, geocode_kind,
                   country, province, locality, district, street, house,
                   locality_lat, locality_lon, locality_status,
                   district_lat, district_lon, district_status,
                   error_message, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE raw_address IN ({placeholders})
            """,
            tuple(raw_addresses),
        )

        return {
            row["raw_address"]: DimAddress.from_db_row(row)
            for row in results
        }

    def save(self, address: DimAddress) -> None:
        """
        Сохранить адрес в кэш.

        StarRocks DUPLICATE KEY model - INSERT заменяет существующую запись.

        Args:
            address: DimAddress для сохранения
        """
        now = datetime.utcnow()
        self.starrocks.execute(
            f"""
            INSERT INTO {self.TABLE_NAME} (
                raw_address, normalized_address, lat, lon, address_status, geocode_kind,
                country, province, locality, district, street, house,
                locality_lat, locality_lon, locality_status,
                district_lat, district_lon, district_status,
                error_message, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s
            )
            """,
            (
                address.raw_address,
                address.normalized_address,
                address.lat,
                address.lon,
                address.address_status.value,
                address.geocode_kind,
                address.country,
                address.province,
                address.locality,
                address.district,
                address.street,
                address.house,
                address.locality_lat,
                address.locality_lon,
                address.locality_status.value if address.locality_status else None,
                address.district_lat,
                address.district_lon,
                address.district_status.value if address.district_status else None,
                address.error_message,
                address.created_at or now,
                now,
            ),
        )

        self.logger.debug(
            "Address saved to cache",
            param("raw_address", address.raw_address[:50]),
            param("address_status", address.address_status.value),
        )

    def save_batch(self, addresses: list[DimAddress]) -> int:
        """
        Сохранить список адресов (batch).

        Args:
            addresses: Список DimAddress

        Returns:
            Количество сохранённых записей
        """
        if not addresses:
            return 0

        now = datetime.utcnow()

        # Подготовка данных для batch insert
        values = []
        for addr in addresses:
            values.append((
                addr.raw_address,
                addr.normalized_address,
                addr.lat,
                addr.lon,
                addr.address_status.value,
                addr.geocode_kind,
                addr.country,
                addr.province,
                addr.locality,
                addr.district,
                addr.street,
                addr.house,
                addr.locality_lat,
                addr.locality_lon,
                addr.locality_status.value if addr.locality_status else None,
                addr.district_lat,
                addr.district_lon,
                addr.district_status.value if addr.district_status else None,
                addr.error_message,
                addr.created_at or now,
                now,
            ))

        # Batch insert через executemany
        with self.starrocks.cursor() as cursor:
            cursor.executemany(
                f"""
                INSERT INTO {self.TABLE_NAME} (
                    raw_address, normalized_address, lat, lon, address_status, geocode_kind,
                    country, province, locality, district, street, house,
                    locality_lat, locality_lon, locality_status,
                    district_lat, district_lon, district_status,
                    error_message, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
                """,
                values,
            )

        self.logger.info(
            "Batch addresses saved to cache",
            param("count", len(addresses)),
        )

        return len(addresses)

    def count(self) -> int:
        """Получить общее количество адресов в кэше."""
        result = self.starrocks.fetch_one(
            f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME}"
        )
        return result["cnt"] if result else 0

    def count_by_status(self) -> dict[str, int]:
        """Получить количество адресов по статусам."""
        results = self.starrocks.fetch_all(
            f"""
            SELECT address_status, COUNT(*) as cnt
            FROM {self.TABLE_NAME}
            GROUP BY address_status
            """
        )
        return {row["address_status"]: row["cnt"] for row in results}

    def get_with_weather_coordinates(self) -> list[DimAddress]:
        """
        Получить все адреса с координатами для погоды.

        Возвращает адреса, у которых есть district или locality координаты.

        Returns:
            Список DimAddress с weather координатами
        """
        results = self.starrocks.fetch_all(
            f"""
            SELECT raw_address, normalized_address, lat, lon, address_status, geocode_kind,
                   country, province, locality, district, street, house,
                   locality_lat, locality_lon, locality_status,
                   district_lat, district_lon, district_status,
                   error_message, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE district_status = 'success' OR locality_status = 'success'
            ORDER BY locality, district
            """
        )

        return [DimAddress.from_db_row(row) for row in results]

    def get_unique_weather_locations(self) -> list[dict]:
        """
        Получить уникальные локации для погоды.

        Группирует по (locality, district) и возвращает координаты.
        Для погоды нужны уникальные координаты, не каждый адрес.

        Returns:
            Список dict с locality, district, lat, lon
        """
        results = self.starrocks.fetch_all(
            f"""
            SELECT
                locality,
                district,
                COALESCE(
                    MAX(CASE WHEN district_status = 'success' THEN district_lat END),
                    MAX(CASE WHEN locality_status = 'success' THEN locality_lat END)
                ) as weather_lat,
                COALESCE(
                    MAX(CASE WHEN district_status = 'success' THEN district_lon END),
                    MAX(CASE WHEN locality_status = 'success' THEN locality_lon END)
                ) as weather_lon
            FROM {self.TABLE_NAME}
            WHERE district_status = 'success' OR locality_status = 'success'
            GROUP BY locality, district
            HAVING weather_lat IS NOT NULL
            ORDER BY locality, district
            """
        )

        return [
            {
                "locality": row["locality"],
                "district": row["district"],
                "weather_lat": row["weather_lat"],
                "weather_lon": row["weather_lon"],
                "location_name": f"{row['locality']}, {row['district']}"
                    if row["district"] else row["locality"],
            }
            for row in results
        ]

    def ensure_table_exists(self) -> bool:
        """
        Проверить/создать таблицу dim_address.

        Returns:
            True если таблица существует или создана
        """
        try:
            result = self.starrocks.fetch_one(
                "SHOW TABLES LIKE %s", (self.TABLE_NAME,)
            )
            if result:
                return True

            self.logger.info(f"Table {self.TABLE_NAME} does not exist, creating...")
            self._create_table()
            self.logger.info(f"Table {self.TABLE_NAME} created successfully")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to ensure {self.TABLE_NAME} table exists",
                e,
            )
            return False

    def _create_table(self) -> None:
        """Create dim_address table in StarRocks."""
        ddl = """
        CREATE TABLE IF NOT EXISTS dim_address (
            raw_address VARCHAR(500) NOT NULL COMMENT 'Сырой адрес (PK)',
            normalized_address VARCHAR(500) COMMENT 'Нормализованный адрес от Yandex',
            lat DOUBLE COMMENT 'Широта точного адреса',
            lon DOUBLE COMMENT 'Долгота точного адреса',
            address_status VARCHAR(20) NOT NULL COMMENT 'success/not_found/error',
            geocode_kind VARCHAR(50) COMMENT 'Точность Yandex: house/street/locality/district',
            country VARCHAR(100) COMMENT 'Страна',
            province VARCHAR(100) COMMENT 'Область/край',
            locality VARCHAR(100) COMMENT 'Город/населённый пункт',
            district VARCHAR(100) COMMENT 'Район города',
            street VARCHAR(200) COMMENT 'Улица',
            house VARCHAR(50) COMMENT 'Номер дома',
            locality_lat DOUBLE COMMENT 'Широта центра города',
            locality_lon DOUBLE COMMENT 'Долгота центра города',
            locality_status VARCHAR(20) COMMENT 'success/not_found/error',
            district_lat DOUBLE COMMENT 'Широта центра района',
            district_lon DOUBLE COMMENT 'Долгота центра района',
            district_status VARCHAR(20) COMMENT 'success/not_found/error',
            error_message VARCHAR(1000) COMMENT 'Сообщение об ошибке',
            created_at DATETIME NOT NULL COMMENT 'Время создания записи',
            updated_at DATETIME NOT NULL COMMENT 'Время последнего обновления'
        )
        ENGINE = OLAP
        DUPLICATE KEY(raw_address)
        COMMENT 'Кэш геокодирования адресов для feature engineering'
        DISTRIBUTED BY HASH(raw_address) BUCKETS 1
        PROPERTIES (
            "replication_num" = "1"
        )
        """
        self.starrocks.execute(ddl)
