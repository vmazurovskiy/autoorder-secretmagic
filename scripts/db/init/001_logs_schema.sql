-- ===================================================================
-- Схема таблицы логов для SecretMagic microservice
-- Использует нативное партиционирование PostgreSQL + LZ4 компрессию
-- ===================================================================

-- Устанавливаем LZ4 как default compression для текстовых полей
ALTER DATABASE secretmagic SET default_toast_compression = 'lz4';

-- Создаём партиционированную таблицу логов
CREATE TABLE IF NOT EXISTS logs (
    -- Время (ДОЛЖНО быть в partition key!)
    timestamp TIMESTAMPTZ NOT NULL,

    -- Идентификация источника
    service_name VARCHAR(50) NOT NULL,
    instance_id VARCHAR(100) NOT NULL,
    node_name VARCHAR(100),
    environment VARCHAR(20) NOT NULL,

    -- Уровень и категория
    level VARCHAR(20) NOT NULL,
    category VARCHAR(50),

    -- Распределённая трассировка
    trace_id VARCHAR(36),
    span_id VARCHAR(20),
    request_id VARCHAR(36),

    -- Код и локация (с LZ4 сжатием для повторяющихся путей)
    function_name VARCHAR(200),
    file_path VARCHAR(500) COMPRESSION lz4,
    line_number INT,

    -- Сообщения (с LZ4 сжатием)
    message TEXT COMPRESSION lz4 NOT NULL,
    error_message TEXT COMPRESSION lz4,
    stack_trace TEXT COMPRESSION lz4,

    -- Контекст (JSONB автоматически сжимается через TOAST)
    context JSONB,

    -- Метрики
    duration_ms INT,

    -- Время вставки
    ingestion_time TIMESTAMPTZ NOT NULL DEFAULT NOW()

) PARTITION BY RANGE (timestamp);

-- Создаём партиции на 6 месяцев вперёд
CREATE TABLE IF NOT EXISTS logs_2025_11 PARTITION OF logs
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE IF NOT EXISTS logs_2025_12 PARTITION OF logs
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

CREATE TABLE IF NOT EXISTS logs_2026_01 PARTITION OF logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE IF NOT EXISTS logs_2026_02 PARTITION OF logs
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE IF NOT EXISTS logs_2026_03 PARTITION OF logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE IF NOT EXISTS logs_2026_04 PARTITION OF logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- Индексы (создаются автоматически на всех партициях!)
CREATE INDEX IF NOT EXISTS idx_logs_service_level_time
    ON logs (service_name, level, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_logs_trace_id
    ON logs (trace_id) WHERE trace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_logs_request_id
    ON logs (request_id) WHERE request_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_logs_context
    ON logs USING GIN (context jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_logs_error
    ON logs (level, timestamp DESC)
    WHERE level IN ('error', 'fatal', 'panic');

CREATE INDEX IF NOT EXISTS idx_logs_environment_time
    ON logs (environment, timestamp DESC);

-- ===================================================================
-- Функции автоматического управления партициями
-- ===================================================================

-- Функция для автоматического создания партиций на N месяцев вперёд
CREATE OR REPLACE FUNCTION create_monthly_log_partitions(
    months_ahead INT DEFAULT 3
)
RETURNS void AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    FOR i IN 0..months_ahead LOOP
        start_date := date_trunc('month', NOW() + (i || ' months')::INTERVAL)::DATE;
        end_date := (start_date + INTERVAL '1 month')::DATE;
        partition_name := 'logs_' || to_char(start_date, 'YYYY_MM');

        -- Проверяем, существует ли партиция
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = 'public' AND tablename = partition_name
        ) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF logs FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
            RAISE NOTICE 'Created partition: %', partition_name;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Функция для удаления партиций старше N дней
CREATE OR REPLACE FUNCTION drop_old_log_partitions(
    retention_days INT DEFAULT 90
)
RETURNS void AS $$
DECLARE
    partition_record RECORD;
    cutoff_date DATE;
    partition_date DATE;
BEGIN
    cutoff_date := (NOW() - (retention_days || ' days')::INTERVAL)::DATE;

    FOR partition_record IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename LIKE 'logs_%'
          AND tablename ~ '^logs_[0-9]{4}_[0-9]{2}$'
    LOOP
        -- Извлекаем дату из имени партиции (logs_2025_11 -> 2025-11-01)
        BEGIN
            partition_date := to_date(
                substring(partition_record.tablename from 6),
                'YYYY_MM'
            );

            IF partition_date < cutoff_date THEN
                EXECUTE format('DROP TABLE %I', partition_record.tablename);
                RAISE NOTICE 'Dropped old partition: %', partition_record.tablename;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Failed to process partition %: %',
                partition_record.tablename, SQLERRM;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения статистики по логам
CREATE OR REPLACE FUNCTION get_log_stats(
    hours_back INT DEFAULT 24
)
RETURNS TABLE (
    service VARCHAR,
    environment VARCHAR,
    level VARCHAR,
    count BIGINT,
    avg_duration_ms NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        service_name::VARCHAR,
        logs.environment::VARCHAR,
        logs.level::VARCHAR,
        COUNT(*)::BIGINT,
        ROUND(AVG(duration_ms), 2)
    FROM logs
    WHERE timestamp >= NOW() - (hours_back || ' hours')::INTERVAL
    GROUP BY service_name, logs.environment, logs.level
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- ===================================================================
-- Пример использования
-- ===================================================================

-- Создать партиции на 6 месяцев вперёд:
-- SELECT create_monthly_log_partitions(6);

-- Удалить партиции старше 90 дней:
-- SELECT drop_old_log_partitions(90);

-- Получить статистику за последние 24 часа:
-- SELECT * FROM get_log_stats(24);
