"""
Yandex Geocoder сервис с кэшированием в StarRocks.

Логика:
1. Проверяем кэш (dim_address) по raw_address
2. Если есть - возвращаем из кэша
3. Если нет - геокодируем:
   a. Точный адрес → lat/lon + компоненты
   b. Город (locality) → locality_lat/lon
   c. Район (locality, district) → district_lat/lon
4. Сохраняем в кэш

API Лимиты:
- Бесплатный tier: 25,000 запросов/день
- Rate limit: до 50 RPS
"""

import re
import time
from typing import Any

import requests

from src.domain.geocode import DimAddress, GeocodeStatus
from src.logger.logger import get_logger
from src.logger.types import Category, param
from src.repository.address_repository import AddressRepository

# Замена сокращений городов на полные названия
CITY_REPLACEMENTS = {
    "МСК": "Москва",
    "СПБ": "Санкт-Петербург",
    "НН": "Нижний Новгород",
    "ЕКБ": "Екатеринбург",
    "КЗН": "Казань",
    "СМР": "Самара",
    "УФА": "Уфа",
    "ЧЕЛ": "Челябинск",
    "РНД": "Ростов-на-Дону",
    "ВЛГ": "Волгоград",
    "НСК": "Новосибирск",
    "КРС": "Краснодар",
    "ВРН": "Воронеж",
    "ПРМ": "Пермь",
    "ОМС": "Омск",
    "ТЮМ": "Тюмень",
}


def clean_address_prefix(address: str) -> str:
    """
    Очистка адреса от префиксов для геокодирования.

    Удаляет:
    - "(закрыта)" или "(закрыта) " в начале
    - "мл " (префикс сети) в начале (case-insensitive)
    - Лишние пробелы
    """
    pattern = r"^\s*(\(закрыта\)\s*)?(?:мл\s+)?"
    cleaned = re.sub(pattern, "", address, flags=re.IGNORECASE)
    return cleaned.strip()


def expand_city_abbreviation(address: str) -> str:
    """Заменить сокращения городов на полные названия."""
    for abbr, full_name in CITY_REPLACEMENTS.items():
        if address.upper().startswith(abbr + " "):
            return full_name + ", " + address[len(abbr) + 1 :]
        if address.lower().startswith(abbr.lower() + " "):
            return full_name + ", " + address[len(abbr) + 1 :]
    return address


def normalize_address_for_geocoding(raw_address: str) -> str:
    """Нормализовать адрес для отправки в Yandex Geocoder."""
    cleaned = clean_address_prefix(raw_address)
    expanded = expand_city_abbreviation(cleaned)
    return expanded


class YandexGeocoder:
    """
    Сервис геокодирования с кэшированием в StarRocks.

    Логика геокодирования:
    1. Геокодируем точный адрес
    2. Если успех и есть locality → геокодируем город
    3. Если успех и есть district → геокодируем район
    """

    BASE_URL = "https://geocode-maps.yandex.ru/1.x/"
    RATE_LIMIT_DELAY = 0.02  # 50 RPS max → 20ms между запросами

    def __init__(
        self,
        api_key: str,
        repository: AddressRepository,
    ) -> None:
        """
        Initialize YandexGeocoder.

        Args:
            api_key: API-ключ Yandex Geocoder
            repository: AddressRepository для кэширования (StarRocks)
        """
        self.api_key = api_key
        self.repository = repository
        self.session = requests.Session()
        self.logger = get_logger().with_category(Category.EXTERNAL_API)

        # Статистика сессии
        self._cache_hits = 0
        self._api_calls = 0

    def geocode(self, raw_address: str) -> DimAddress:
        """
        Геокодировать адрес (с кэшированием).

        Args:
            raw_address: Сырой адрес для геокодирования

        Returns:
            DimAddress с результатами геокодирования
        """
        # 1. Проверяем кэш
        cached = self.repository.get_by_raw_address(raw_address)
        if cached is not None:
            self._cache_hits += 1
            self.logger.debug(
                "Geocode cache hit",
                param("raw_address", raw_address[:50]),
            )
            return cached

        # 2. Геокодируем
        result = self._geocode_full(raw_address)

        # 3. Сохраняем в кэш
        self.repository.save(result)

        return result

    def geocode_batch(
        self,
        raw_addresses: list[str],
        progress_callback: Any = None,
    ) -> list[DimAddress]:
        """
        Геокодировать список адресов (с кэшированием).

        Args:
            raw_addresses: Список сырых адресов
            progress_callback: Опциональный callback для прогресса

        Returns:
            Список DimAddress в том же порядке
        """
        if not raw_addresses:
            return []

        total = len(raw_addresses)
        self.logger.info(
            "Starting batch geocoding",
            param("total_addresses", total),
        )

        # 1. Batch-проверка кэша
        cached_map = self.repository.get_by_raw_addresses(raw_addresses)
        cached_count = len(cached_map)
        self._cache_hits += cached_count

        self.logger.info(
            "Batch cache lookup complete",
            param("cached", cached_count),
            param("to_geocode", total - cached_count),
        )

        # 2. Собираем результаты и запрашиваем недостающие
        results: list[DimAddress] = []
        to_save: list[DimAddress] = []

        for i, raw_address in enumerate(raw_addresses, 1):
            if raw_address in cached_map:
                results.append(cached_map[raw_address])
            else:
                result = self._geocode_full(raw_address)
                results.append(result)
                to_save.append(result)

            # Progress callback
            if progress_callback and i % 50 == 0:
                progress_callback(i, total)

        # 3. Batch-сохранение новых результатов
        if to_save:
            self.repository.save_batch(to_save)
            self.logger.info(
                "Batch geocoding complete",
                param("new_cached", len(to_save)),
            )

        return results

    def _geocode_full(self, raw_address: str) -> DimAddress:
        """
        Полное геокодирование адреса (3 запроса).

        1. Точный адрес
        2. Город (если есть locality)
        3. Район (если есть district)

        Args:
            raw_address: Сырой адрес

        Returns:
            DimAddress с заполненными полями
        """
        result = DimAddress(raw_address=raw_address)

        # 1. Геокодируем точный адрес
        normalized = normalize_address_for_geocoding(raw_address)
        address_response = self._call_yandex_api(normalized)

        if not address_response:
            result.address_status = GeocodeStatus.NOT_FOUND
            return result

        # Заполняем данные точного адреса
        result.address_status = GeocodeStatus.SUCCESS
        result.normalized_address = address_response.get("formatted_address")
        result.lat = address_response.get("lat")
        result.lon = address_response.get("lon")
        result.geocode_kind = address_response.get("kind")
        result.country = address_response.get("country")
        result.province = address_response.get("province")
        result.locality = address_response.get("locality")
        result.district = address_response.get("district")
        result.street = address_response.get("street")
        result.house = address_response.get("house")

        # 2. Геокодируем город (если есть locality)
        if result.locality:
            locality_response = self._call_yandex_api(result.locality)
            if locality_response:
                result.locality_status = GeocodeStatus.SUCCESS
                result.locality_lat = locality_response.get("lat")
                result.locality_lon = locality_response.get("lon")
            else:
                result.locality_status = GeocodeStatus.NOT_FOUND

        # 3. Геокодируем район (если есть district)
        if result.district and result.locality:
            district_query = f"{result.locality}, {result.district}"
            district_response = self._call_yandex_api(district_query)
            if district_response:
                result.district_status = GeocodeStatus.SUCCESS
                result.district_lat = district_response.get("lat")
                result.district_lon = district_response.get("lon")
            else:
                result.district_status = GeocodeStatus.NOT_FOUND

        return result

    def _call_yandex_api(self, query: str) -> dict[str, Any] | None:
        """
        Вызвать Yandex Geocoder API.

        Args:
            query: Строка для геокодирования

        Returns:
            Dict с результатом или None если не найдено
        """
        self._api_calls += 1

        params = {
            "apikey": self.api_key,
            "geocode": query,
            "format": "json",
            "lang": "ru_RU",
            "results": 1,
        }

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            # Rate limiting
            time.sleep(self.RATE_LIMIT_DELAY)

            # Парсинг ответа
            return self._parse_response(data)

        except requests.RequestException as e:
            self.logger.error(
                "Yandex Geocoder API error",
                e,
                param("query", query[:50]),
            )
            return None

    def _parse_response(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Парсинг ответа Yandex Geocoder API.

        Returns:
            Dict с полями или None если не найдено
        """
        try:
            feature_members = data["response"]["GeoObjectCollection"]["featureMember"]

            if not feature_members:
                return None

            geo_object = feature_members[0]["GeoObject"]
            point = geo_object["Point"]["pos"].split()
            lon, lat = float(point[0]), float(point[1])

            meta = geo_object["metaDataProperty"]["GeocoderMetaData"]
            formatted_address = meta["Address"]["formatted"]
            components = meta["Address"].get("Components", [])
            kind = meta.get("kind", "unknown")

            # Парсинг компонентов
            parsed = self._parse_components(components)

            return {
                "lat": lat,
                "lon": lon,
                "formatted_address": formatted_address,
                "kind": kind,
                **parsed,
            }

        except (KeyError, IndexError, ValueError) as e:
            self.logger.warn(
                "Failed to parse Yandex response",
                param("error", str(e)),
            )
            return None

    @staticmethod
    def _parse_components(components: list[dict[str, str]]) -> dict[str, str | None]:
        """Парсинг массива Components из Yandex API."""
        result: dict[str, str | None] = {
            "country": None,
            "province": None,
            "locality": None,
            "district": None,
            "street": None,
            "house": None,
        }

        for component in components:
            kind = component.get("kind")
            name = component.get("name")
            if kind in result:
                result[kind] = name

        return result

    def get_stats(self) -> dict[str, int]:
        """Получить статистику сессии."""
        return {
            "cache_hits": self._cache_hits,
            "api_calls": self._api_calls,
            "total_requests": self._cache_hits + self._api_calls,
        }

    def reset_stats(self) -> None:
        """Сбросить статистику сессии."""
        self._cache_hits = 0
        self._api_calls = 0
