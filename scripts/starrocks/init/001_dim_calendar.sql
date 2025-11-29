-- dim_calendar: Календарный справочник для feature engineering
-- Общий для всех клиентов, используется для:
-- 1. Расчёта календарных фич
-- 2. Преобразования sparse → dense данных по временным рядам
--
-- Таблица заполняется программно через CalendarBuilder
-- ~55 колонок, ~2000 строк (2020-2025)

CREATE TABLE IF NOT EXISTS dim_calendar (
    -- Primary key
    `date` DATE NOT NULL COMMENT 'Календарная дата',

    -- Base components (9)
    iso_year INT NOT NULL COMMENT 'ISO год (год ISO-недели)',
    iso_week INT NOT NULL COMMENT 'ISO неделя (1-53)',
    iso_dow TINYINT NOT NULL COMMENT 'ISO день недели: 1=Пн...7=Вс',
    `year` INT NOT NULL COMMENT 'Григорианский год',
    `month` TINYINT NOT NULL COMMENT 'Месяц (1-12)',
    `day` TINYINT NOT NULL COMMENT 'День месяца (1-31)',
    `quarter` TINYINT NOT NULL COMMENT 'Квартал (1-4)',
    day_of_year SMALLINT NOT NULL COMMENT 'День года (1-366)',

    -- Cyclic features for neural networks (10)
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

    -- Binary weekday flags (7)
    is_monday TINYINT NOT NULL DEFAULT 0 COMMENT 'Понедельник',
    is_tuesday TINYINT NOT NULL DEFAULT 0 COMMENT 'Вторник',
    is_wednesday TINYINT NOT NULL DEFAULT 0 COMMENT 'Среда',
    is_thursday TINYINT NOT NULL DEFAULT 0 COMMENT 'Четверг',
    is_friday TINYINT NOT NULL DEFAULT 0 COMMENT 'Пятница',
    is_saturday TINYINT NOT NULL DEFAULT 0 COMMENT 'Суббота',
    is_sunday TINYINT NOT NULL DEFAULT 0 COMMENT 'Воскресенье',

    -- Weekend/holiday flags from isdayoff.ru (5)
    is_weekend_iso BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Суббота/воскресенье по ISO',
    is_day_off_official BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Официальный нерабочий день',
    is_weekend_official BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Официальный выходной (day_off AND weekend_iso)',
    is_holiday_official BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Официальный праздник (python-holidays)',
    is_preholiday_official BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Сокращённый рабочий день',

    -- Holiday block features (4)
    within_holiday_block BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'День внутри праздничного блока',
    holiday_block_pos INT NULL COMMENT 'Позиция в блоке (0-indexed), NULL если вне блока',
    is_preholiday_start BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'День перед началом праздничного блока',
    is_preholiday_start_working BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Рабочий день перед праздничным блоком',

    -- Transition features (8)
    is_last_off_before_work BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Последний нерабочий перед рабочим',
    is_first_work_after_off BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Первый рабочий после нерабочих',
    is_last_weekend_iso_before_work BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Последний ISO выходной перед работой',
    is_last_official_weekend_before_work BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Последний официальный выходной перед работой',
    is_pre_weekend_iso BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Пятница (канун ISO-выходных)',
    is_pre_weekend_official BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Завтра официальный нерабочий',
    is_working_weekend BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'ISO выходной, но рабочий день',
    is_day_off_non_weekend BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Будний, но нерабочий',

    -- Russian holidays hardcoded (8)
    is_new_year_holidays TINYINT NOT NULL DEFAULT 0 COMMENT 'Новогодние каникулы (1-8 января)',
    is_defender_day TINYINT NOT NULL DEFAULT 0 COMMENT 'День защитника Отечества (23 февраля)',
    is_womens_day TINYINT NOT NULL DEFAULT 0 COMMENT 'Международный женский день (8 марта)',
    is_labour_day TINYINT NOT NULL DEFAULT 0 COMMENT 'Праздник Весны и Труда (1 мая)',
    is_victory_day TINYINT NOT NULL DEFAULT 0 COMMENT 'День Победы (9 мая)',
    is_russia_day TINYINT NOT NULL DEFAULT 0 COMMENT 'День России (12 июня)',
    is_unity_day TINYINT NOT NULL DEFAULT 0 COMMENT 'День народного единства (4 ноября)',
    is_orthodox_christmas TINYINT NOT NULL DEFAULT 0 COMMENT 'Рождество Христово (7 января)',

    -- Business cycle features (3)
    is_end_of_month TINYINT NOT NULL DEFAULT 0 COMMENT 'Последние 3 дня месяца',
    days_since_month_start_norm DOUBLE NOT NULL COMMENT 'Дни от начала месяца (0.0-1.0)',
    is_quarter_end TINYINT NOT NULL DEFAULT 0 COMMENT 'Последние 7 дней квартала',

    -- Seasons (2)
    season_meteo VARCHAR(3) NOT NULL COMMENT 'Метеосезон: DJF/MAM/JJA/SON',
    season_iso VARCHAR(10) NOT NULL COMMENT 'Сезон с ISO-годом, например DJF-2024'
)
ENGINE = OLAP
DUPLICATE KEY(`date`)
COMMENT 'Календарный справочник для feature engineering (~55 колонок)'
DISTRIBUTED BY HASH(`date`) BUCKETS 1
PROPERTIES (
    "replication_num" = "1",
    "in_memory" = "true"
);
