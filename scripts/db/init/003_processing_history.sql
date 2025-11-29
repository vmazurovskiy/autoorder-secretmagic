-- Таблица processing_history: история обработки данных из StarRocks
-- Хранит информацию о каждом запуске feature engineering для аудита и инкрементальной обработки

CREATE TABLE IF NOT EXISTS processing_history (
    id SERIAL PRIMARY KEY,

    -- Идентификация клиента и таблицы
    client_id UUID NOT NULL REFERENCES clients(id),
    table_name VARCHAR(100) NOT NULL,  -- 'c2_sales', 'c2_stock', 'c2_bom' и т.д.

    -- Что обработали
    last_ingestion_time TIMESTAMP WITH TIME ZONE NOT NULL,  -- до какого ingestion_time обработали
    records_processed INTEGER NOT NULL DEFAULT 0,
    batch_id VARCHAR(36),  -- ID батча из StarRocks (опционально)

    -- Когда и как обработали
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processing_duration_ms INTEGER,

    -- Статус обработки
    status VARCHAR(20) NOT NULL DEFAULT 'completed',  -- completed, failed, partial
    error_message TEXT,

    -- Метаданные (опционально, для отладки)
    metadata JSONB DEFAULT '{}'
);

-- Индекс для быстрого поиска последней успешной обработки по клиенту и таблице
CREATE INDEX IF NOT EXISTS idx_processing_history_client_table
ON processing_history(client_id, table_name, processed_at DESC);

-- Индекс по статусу для мониторинга ошибок
CREATE INDEX IF NOT EXISTS idx_processing_history_status
ON processing_history(status) WHERE status != 'completed';

-- Индекс по времени для очистки старых записей
CREATE INDEX IF NOT EXISTS idx_processing_history_processed_at
ON processing_history(processed_at);

-- Комментарии
COMMENT ON TABLE processing_history IS 'История обработки данных из StarRocks для feature engineering. Каждая запись = один запуск обработки.';
COMMENT ON COLUMN processing_history.table_name IS 'Имя таблицы в StarRocks: c{org_id}_sales, c{org_id}_stock и т.д.';
COMMENT ON COLUMN processing_history.last_ingestion_time IS 'До какого ingestion_time включительно обработаны данные. Следующая обработка начнётся с > этого значения.';
COMMENT ON COLUMN processing_history.status IS 'Статус: completed (успешно), failed (ошибка), partial (частичная обработка)';
COMMENT ON COLUMN processing_history.metadata IS 'Дополнительные данные: features_calculated, date_range и т.д.';
