-- dim_address: Кэш геокодирования адресов
-- Хранит результаты нормализации адресов через Yandex Geocoder
-- Используется для:
-- 1. Кэширования геокодирования (каждый адрес запрашивается 1 раз)
-- 2. Получения координат для погодных фич (district_lat/lon или locality_lat/lon)
-- 3. JOIN с фактовыми таблицами (sales, stock) по raw_address

CREATE TABLE IF NOT EXISTS dim_address (
    -- Ключ
    raw_address VARCHAR(500) NOT NULL COMMENT 'Сырой адрес (PK)',

    -- Результат геокодирования точного адреса
    normalized_address VARCHAR(500) COMMENT 'Нормализованный адрес от Yandex',
    lat DOUBLE COMMENT 'Широта точного адреса',
    lon DOUBLE COMMENT 'Долгота точного адреса',
    address_status VARCHAR(20) NOT NULL COMMENT 'success/not_found/error',
    geocode_kind VARCHAR(50) COMMENT 'Точность Yandex: house/street/locality/district',

    -- Структурированные компоненты адреса (как вернул Yandex)
    country VARCHAR(100) COMMENT 'Страна',
    province VARCHAR(100) COMMENT 'Область/край/город фед. значения',
    locality VARCHAR(100) COMMENT 'Город/населённый пункт',
    district VARCHAR(100) COMMENT 'Район города',
    street VARCHAR(200) COMMENT 'Улица',
    house VARCHAR(50) COMMENT 'Номер дома',

    -- Геокодирование города (запрос: locality)
    locality_lat DOUBLE COMMENT 'Широта центра города',
    locality_lon DOUBLE COMMENT 'Долгота центра города',
    locality_status VARCHAR(20) COMMENT 'success/not_found/error, NULL если locality пуст',

    -- Геокодирование района (запрос: "locality, district")
    district_lat DOUBLE COMMENT 'Широта центра района',
    district_lon DOUBLE COMMENT 'Долгота центра района',
    district_status VARCHAR(20) COMMENT 'success/not_found/error, NULL если district пуст',

    -- Метаданные
    error_message VARCHAR(1000) COMMENT 'Сообщение об ошибке (если есть)',
    created_at DATETIME NOT NULL COMMENT 'Время создания записи',
    updated_at DATETIME NOT NULL COMMENT 'Время последнего обновления'
)
ENGINE = OLAP
DUPLICATE KEY(raw_address)
COMMENT 'Кэш геокодирования адресов для feature engineering'
DISTRIBUTED BY HASH(raw_address) BUCKETS 1
PROPERTIES (
    "replication_num" = "1"
);

-- Примечание: Для выбора координат погоды использовать:
-- COALESCE(district_lat, locality_lat) as weather_lat
-- COALESCE(district_lon, locality_lon) as weather_lon
-- WHERE COALESCE(district_status, locality_status) = 'success'
