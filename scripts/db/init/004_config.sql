-- config: Глобальные настройки микросервиса
-- Каждый параметр - отдельная строка

CREATE TABLE IF NOT EXISTS config (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(500) NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(100) NOT NULL DEFAULT 'system'
);

-- Индекс для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_config_updated_at ON config(updated_at);

-- Комментарий к таблице
COMMENT ON TABLE config IS 'Глобальные настройки микросервиса SecretMagic';
COMMENT ON COLUMN config.key IS 'Уникальный ключ параметра';
COMMENT ON COLUMN config.value IS 'Значение параметра (строка)';
COMMENT ON COLUMN config.description IS 'Описание параметра';
COMMENT ON COLUMN config.updated_at IS 'Время последнего обновления';
COMMENT ON COLUMN config.updated_by IS 'Кто обновил: system, admin, api';

-- Начальные значения для календаря
INSERT INTO config (key, value, description, updated_by) VALUES
    ('calendar_start_date', '2020-01-01', 'Начальная дата календаря dim_calendar', 'system'),
    ('calendar_future_upload', '10.12', 'День.Месяц для загрузки следующего года из isdayoff.ru', 'system'),
    ('calendar_region', 'ru', 'Регион для праздников (ru, lt, kz и т.д.)', 'system')
ON CONFLICT (key) DO NOTHING;
