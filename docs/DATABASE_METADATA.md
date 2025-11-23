# База данных метаданных - SecretMagic

**Технология:** PostgreSQL 16+

Хранит метаданные, конфигурации feature engineering, параметры BOM explosion, расписания обработки и аудит изменений.

## Принципы работы

### 1. Event Sourcing
**Создавать новые записи вместо UPDATE.**

```sql
-- ❌ НЕ ТАК
UPDATE feature_configs SET config = '...' WHERE id = '...';

-- ✅ ТАК
INSERT INTO feature_configs (client_id, feature_type, config, is_active)
VALUES ('...', '...', '...', true);

-- Деактивировать старую версию
UPDATE feature_configs SET is_active = false
WHERE client_id = '...' AND id != NEW.id;
```

### 2. Версионирование
Используйте `is_active` и `created_at` для версионирования:
- `is_active = true` - текущая версия
- `is_active = false` - история
- `created_at` - временная метка версии

### 3. Мультитенантность (StarRocks)

**Режимы хранения данных** определяются на уровне клиента:
- `tenant_mode = 'prefixed_tables'` - отдельные таблицы `c{org_id}_features` (дефолт)
- `tenant_mode = 'dedicated_db'` - отдельная database `client_{org_id}`
- `tenant_mode = 'shared'` - общие таблицы с полем `tenant_id` (опционально)

**Важно:** Перед обработкой данных требуется подтверждение конфигурации через флаг `config_confirmed`:

```sql
-- 1. Создать клиента с tenant_mode
INSERT INTO clients (name, organization_id, tenant_mode, features_enabled, status)
VALUES (
  'ООО "Гастрономия"',
  '2',
  'prefixed_tables',  -- дефолт для большинства
  '{"feature_engineering": true, "bom_explosion": true}'::jsonb,
  'active'
);

-- 2. Подтвердить конфигурацию перед обработкой данных
UPDATE clients
SET config_confirmed = true,
    config_confirmed_at = NOW(),
    config_confirmed_by = 'admin@example.com'
WHERE id = 'uuid-client';

-- Обработка данных блокируется до config_confirmed = true
```

**Миграция между режимами:**
- `prefixed_tables → dedicated_db`: `RENAME TABLE c2_features TO client_2.features`
- `shared → dedicated_db`: двойная запись + перепаковка партиций

**Миграции схемы:**
- Используется ALTER TABLE для изменения структуры таблиц
- Blue/green deployment приложения для zero-downtime обновлений

## Структура таблиц

### Клиенты
**`clients`** - клиенты платформы AutoOrder

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Уникальный идентификатор |
| `name` | VARCHAR(255) | Название организации |
| `organization_id` | VARCHAR(100) | ID организации (для routing в StarRocks) |
| `tenant_mode` | VARCHAR(20) | Режим хранения данных в StarRocks:<br/>- `prefixed_tables` (дефолт)<br/>- `dedicated_db`<br/>- `shared` |
| `features_enabled` | JSONB | Включенные функции: `{"feature_engineering": true, "bom_explosion": true}` |
| `config_confirmed` | BOOLEAN | Подтверждена ли конфигурация для обработки данных |
| `config_confirmed_at` | TIMESTAMP | Время подтверждения конфигурации |
| `config_confirmed_by` | VARCHAR(100) | Кто подтвердил конфигурацию |
| `contact_email` | VARCHAR(255) | Контактный email |
| `contact_phone` | VARCHAR(50) | Контактный телефон |
| `status` | VARCHAR(20) | Статус: `active`, `suspended`, `archived` |
| `created_at` | TIMESTAMP | Время создания |
| `updated_at` | TIMESTAMP | Время последнего обновления |

**Ключевые особенности:**
- `tenant_mode` определяет структуру таблиц в StarRocks
- `config_confirmed = true` обязателен перед обработкой данных
- `organization_id` используется в именовании таблиц (`c{org_id}_features`)

### Справочники
- `data_types` - типы данных (features, bom, timeseries, aggregations...)
- `feature_types` - типы фич (ema, ma, std, lags, seasonality, weather, promo)

### Feature Engineering
- `feature_configs` - конфигурации feature engineering (версионирование)
- `feature_metadata` - метаданные о созданных фичах (имена, типы, семантика NaN)

### BOM Explosion
- `bom_configs` - конфигурации BOM explosion (max_levels, include_produced_at)
- `bom_explosion_status` - статус обработки BOM для клиентов

### Расписания
- `scheduler_config` - глобальные дефолтные настройки планировщика
- `client_processing_schedule` - индивидуальные настройки обработки клиентов (interval/daily/weekly)

### Обработка
- `batches` - метаданные batch-обработок
- `processing_logs` - детальные логи обработки

### Аудит
- `audit_log` - история всех изменений

## Типовые запросы

### Получить актуальную конфигурацию фич
```sql
SELECT * FROM feature_configs
WHERE client_id = '...'
  AND feature_type = 'ema'
  AND is_active = true
ORDER BY created_at DESC
LIMIT 1;
```

### Получить историю изменений конфигурации
```sql
SELECT version, config, created_at, created_by
FROM feature_configs
WHERE client_id = '...'
  AND feature_type = 'weather'
ORDER BY created_at DESC;
```

### Создать конфигурацию feature engineering для клиента
```sql
-- 1. Создать конфигурацию EMA фич
INSERT INTO feature_configs (client_id, feature_type, config, is_active)
VALUES (
  'uuid-client',
  'ema',
  '{
    "window_days": 90,
    "alpha": 0.5,
    "min_samples": 7,
    "nan_strategy": "decay"
  }'::jsonb,
  true
);

-- 2. Создать конфигурацию сезонности
INSERT INTO feature_configs (client_id, feature_type, config, is_active)
VALUES (
  'uuid-client',
  'seasonality',
  '{
    "include_day_of_week": true,
    "include_month": true,
    "include_holidays": true
  }'::jsonb,
  true
);

-- 3. Создать конфигурацию BOM explosion
INSERT INTO bom_configs (client_id, max_levels, include_produced_at, cycle_detection, is_active)
VALUES (
  'uuid-client',
  5,
  true,
  true,
  true
);
```

### Получить активные фичи клиента
```sql
SELECT
  fc.id,
  fc.feature_type,
  fc.config,
  fc.created_at
FROM feature_configs fc
WHERE fc.client_id = 'uuid-client'
  AND fc.is_active = true
ORDER BY fc.feature_type;
```

### Получить статус обработки BOM
```sql
SELECT
  c.name,
  c.organization_id,
  bes.last_processed_at,
  bes.records_processed,
  bes.status,
  bes.error_message
FROM clients c
LEFT JOIN bom_explosion_status bes ON c.id = bes.client_id
WHERE c.status = 'active'
ORDER BY bes.last_processed_at DESC;
```

## Миграции

Схема инициализируется автоматически при первом запуске через:
```
/scripts/db/init/001_schema.sql
```

Для новых миграций создавайте файлы:
```
/scripts/db/migrations/002_add_something.sql
/scripts/db/migrations/003_add_another.sql
```

## Подключение

### Из Python приложения
```python
import psycopg2
from psycopg2.pool import SimpleConnectionPool

# Создание connection pool
db_pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=cfg.db.host,
    port=cfg.db.port,
    user=cfg.db.user,
    password=cfg.db.password,
    dbname=cfg.db.name,
    sslmode=cfg.db.ssl_mode
)

# Использование
conn = db_pool.getconn()
try:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM clients WHERE status = 'active'")
        rows = cur.fetchall()
finally:
    db_pool.putconn(conn)
```

### Из контейнера
```bash
docker compose exec postgres psql -U secretmagic -d secretmagic
```

### С хоста (для dev)
```bash
docker compose exec postgres psql -U secretmagic -d secretmagic
```

## Бэкапы

```bash
# Создать бэкап
docker compose exec postgres pg_dump -U secretmagic secretmagic > backup.sql

# Восстановить
docker compose exec -T postgres psql -U secretmagic secretmagic < backup.sql
```

## Мониторинг

### Размер таблиц
```sql
SELECT
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Активные подключения
```sql
SELECT count(*) FROM pg_stat_activity
WHERE datname = 'secretmagic';
```

### Медленные запросы
```sql
SELECT query, calls, total_exec_time, mean_exec_time
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = 'secretmagic')
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Типичные таблицы метаданных

### feature_configs
```sql
CREATE TABLE feature_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    feature_type VARCHAR(50) NOT NULL,  -- ema, ma, std, lags, seasonality, weather, promo
    config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    version INTEGER GENERATED ALWAYS AS IDENTITY,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    CONSTRAINT unique_active_feature UNIQUE (client_id, feature_type, is_active)
        WHERE is_active = true
);
```

### bom_configs
```sql
CREATE TABLE bom_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    max_levels INTEGER NOT NULL DEFAULT 5,
    include_produced_at BOOLEAN DEFAULT true,
    cycle_detection BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    version INTEGER GENERATED ALWAYS AS IDENTITY,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    CONSTRAINT unique_active_bom UNIQUE (client_id, is_active)
        WHERE is_active = true
);
```

### processing_logs (логирование в PostgreSQL)
```sql
CREATE TABLE logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    level VARCHAR(10) NOT NULL,  -- debug, info, warn, error
    message TEXT NOT NULL,
    error TEXT,
    context JSONB,  -- {client_id, batch_id, feature_type, ...}
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_logs_timestamp ON logs(timestamp DESC);
CREATE INDEX idx_logs_level ON logs(level) WHERE level IN ('error', 'warn');
CREATE INDEX idx_logs_context_client ON logs((context->>'client_id'));
```
