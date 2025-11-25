-- Таблица clients: конфигурация клиентов для SecretMagic
-- Источник данных: события clients_updated из messenger (Redis Streams)
-- Паттерн: Event Carried State Transfer (события содержат полное состояние)

CREATE TABLE IF NOT EXISTS clients (
    -- Идентификация
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,

    -- Контакты
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),

    -- Статус
    status VARCHAR(50) NOT NULL DEFAULT 'active',

    -- Конфигурация features (JSONB для гибкости)
    features_enabled JSONB NOT NULL DEFAULT '{}',

    -- Подтверждение конфигурации
    config_confirmed BOOLEAN NOT NULL DEFAULT false,
    config_confirmed_by VARCHAR(255),
    config_confirmed_at TIMESTAMP WITH TIME ZONE,

    -- Метаданные
    source VARCHAR(255),

    -- Временные метки
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Синхронизация с источником
    synced_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Индекс по organization_id для быстрого поиска клиентов организации
CREATE INDEX IF NOT EXISTS idx_clients_organization_id ON clients(organization_id);

-- Индекс по status для фильтрации активных клиентов
CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);

-- Индекс по features_enabled для поиска клиентов с определенными фичами
CREATE INDEX IF NOT EXISTS idx_clients_features ON clients USING GIN (features_enabled);

-- Комментарии
COMMENT ON TABLE clients IS 'Конфигурация клиентов для SecretMagic (синхронизируется из integrator через messenger)';
COMMENT ON COLUMN clients.features_enabled IS 'JSONB карта включенных бизнес-функций: {"autoorder": true, "demand_forecast": false}';
COMMENT ON COLUMN clients.synced_at IS 'Timestamp последней синхронизации из messenger (для мониторинга актуальности)';
