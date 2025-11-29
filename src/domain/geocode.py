"""Geocode domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class GeocodeStatus(str, Enum):
    """Статус геокодирования."""

    SUCCESS = "success"      # Адрес успешно найден
    NOT_FOUND = "not_found"  # Адрес не найден в Yandex
    ERROR = "error"          # Ошибка API


@dataclass
class DimAddress:
    """
    Результат геокодирования адреса для dim_address (StarRocks).

    Хранит:
    - Результат геокодирования точного адреса
    - Структурированные компоненты адреса
    - Координаты города (locality)
    - Координаты района (district)
    """

    # Ключ
    raw_address: str

    # Результат геокодирования точного адреса
    normalized_address: str | None = None
    lat: float | None = None
    lon: float | None = None
    address_status: GeocodeStatus = GeocodeStatus.NOT_FOUND
    geocode_kind: str | None = None  # house, street, locality, district

    # Структурированные компоненты
    country: str | None = None
    province: str | None = None      # Область/край
    locality: str | None = None      # Город/населённый пункт
    district: str | None = None      # Район города
    street: str | None = None
    house: str | None = None

    # Координаты города (запрос: locality)
    locality_lat: float | None = None
    locality_lon: float | None = None
    locality_status: GeocodeStatus | None = None

    # Координаты района (запрос: "locality, district")
    district_lat: float | None = None
    district_lon: float | None = None
    district_status: GeocodeStatus | None = None

    # Метаданные
    error_message: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_address_success(self) -> bool:
        """Успешно ли геокодирован точный адрес."""
        return self.address_status == GeocodeStatus.SUCCESS

    @property
    def has_coordinates(self) -> bool:
        """Есть ли координаты точного адреса."""
        return self.lat is not None and self.lon is not None

    @property
    def weather_lat(self) -> float | None:
        """Широта для погоды (район → город → None)."""
        if self.district_status == GeocodeStatus.SUCCESS and self.district_lat:
            return self.district_lat
        if self.locality_status == GeocodeStatus.SUCCESS and self.locality_lat:
            return self.locality_lat
        return None

    @property
    def weather_lon(self) -> float | None:
        """Долгота для погоды (район → город → None)."""
        if self.district_status == GeocodeStatus.SUCCESS and self.district_lon:
            return self.district_lon
        if self.locality_status == GeocodeStatus.SUCCESS and self.locality_lon:
            return self.locality_lon
        return None

    @property
    def has_weather_coordinates(self) -> bool:
        """Есть ли координаты для погоды."""
        return self.weather_lat is not None and self.weather_lon is not None

    @property
    def weather_location_name(self) -> str | None:
        """Название локации для погоды."""
        if self.district_status == GeocodeStatus.SUCCESS and self.district:
            return f"{self.locality}, {self.district}"
        if self.locality_status == GeocodeStatus.SUCCESS and self.locality:
            return self.locality
        return None

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать в словарь для сериализации."""
        return {
            "raw_address": self.raw_address,
            "normalized_address": self.normalized_address,
            "lat": self.lat,
            "lon": self.lon,
            "address_status": self.address_status.value,
            "geocode_kind": self.geocode_kind,
            "country": self.country,
            "province": self.province,
            "locality": self.locality,
            "district": self.district,
            "street": self.street,
            "house": self.house,
            "locality_lat": self.locality_lat,
            "locality_lon": self.locality_lon,
            "locality_status": self.locality_status.value if self.locality_status else None,
            "district_lat": self.district_lat,
            "district_lon": self.district_lon,
            "district_status": self.district_status.value if self.district_status else None,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "DimAddress":
        """
        Создать из строки БД (StarRocks).

        Args:
            row: Строка из StarRocks (dict)

        Returns:
            DimAddress instance
        """
        # Parse status enums
        address_status = GeocodeStatus(row.get("address_status", "not_found"))

        locality_status_val = row.get("locality_status")
        locality_status = GeocodeStatus(locality_status_val) if locality_status_val else None

        district_status_val = row.get("district_status")
        district_status = GeocodeStatus(district_status_val) if district_status_val else None

        return cls(
            raw_address=row["raw_address"],
            normalized_address=row.get("normalized_address"),
            lat=row.get("lat"),
            lon=row.get("lon"),
            address_status=address_status,
            geocode_kind=row.get("geocode_kind"),
            country=row.get("country"),
            province=row.get("province"),
            locality=row.get("locality"),
            district=row.get("district"),
            street=row.get("street"),
            house=row.get("house"),
            locality_lat=row.get("locality_lat"),
            locality_lon=row.get("locality_lon"),
            locality_status=locality_status,
            district_lat=row.get("district_lat"),
            district_lon=row.get("district_lon"),
            district_status=district_status,
            error_message=row.get("error_message"),
            created_at=row.get("created_at", datetime.utcnow()),
            updated_at=row.get("updated_at", datetime.utcnow()),
        )

    @classmethod
    def not_found(cls, raw_address: str, error_message: str | None = None) -> "DimAddress":
        """Создать запись для ненайденного адреса."""
        return cls(
            raw_address=raw_address,
            address_status=GeocodeStatus.NOT_FOUND,
            error_message=error_message,
        )

    @classmethod
    def error(cls, raw_address: str, error_message: str) -> "DimAddress":
        """Создать запись с ошибкой."""
        return cls(
            raw_address=raw_address,
            address_status=GeocodeStatus.ERROR,
            error_message=error_message,
        )
