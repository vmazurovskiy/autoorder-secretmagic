# Конфигурация SecretMagic

Система конфигурации с поддержкой Docker Secrets, переменных окружения и defaults.

## Приоритет загрузки

```
Docker Secrets (/run/secrets/) > Environment Variables > Defaults
```

Это обеспечивает плавный переход от Docker Secrets к Kubernetes Secrets (volumeMount в /run/secrets/).

## Структура конфигурации

### GlobalConfig (immutable)

Загружается **один раз** при старте приложения и не изменяется во время работы.

```python
@dataclass
class GlobalConfig:
    service: ServiceConfig
    database: DatabaseConfig
    starrocks: StarRocksConfig
    features: FeatureEngineeringConfig
    bom: BOMConfig
    server: ServerConfig
    logging: LoggingConfig
```

### JobConfig (immutable)

Создаётся для **каждого клиента** при выполнении job и обеспечивает полную изоляцию потоков.

```python
@dataclass
class JobConfig:
    # Идентификация клиента
    client_id: UUID
    client_name: str
    organization_id: str

    # Tenant mode определяет, как хранятся данные клиента
    tenant_mode: str  # shared, dedicated_schema, dedicated_db

    # StarRocks routing
    starrocks_database: str
    starrocks_schema: str
    starrocks_table_prefix: str

    # Бизнес-функции клиента
    features_enabled: Dict[str, bool]

    # Feature engineering параметры
    feature_window_days: int
    min_samples_threshold: int
    nan_handling_strategy: str  # decay, fill_zero, drop

    # BOM explosion параметры
    bom_max_levels: int
    bom_include_produced_at: bool

    # Параметры обработки
    batch_size: int
    timeout_seconds: int
```

## Переменные окружения

### Database (PostgreSQL)

| Переменная | Описание | Default |
|-----------|----------|---------|
| `DB_HOST` | Хост PostgreSQL | `localhost` |
| `DB_PORT` | Порт PostgreSQL | `5432` |
| `DB_NAME` | Имя базы данных | `secretmagic` |
| `DB_USER` | Пользователь БД | `secretmagic` |
| `DB_PASSWORD` | Пароль (из Docker Secrets) | - |
| `DB_SSL_MODE` | SSL режим | `disable` |
| `DB_MAX_OPEN_CONNS` | Макс открытых соединений | `25` |
| `DB_MAX_IDLE_CONNS` | Макс idle соединений | `5` |

### StarRocks

| Переменная | Описание | Default |
|-----------|----------|---------|
| `STARROCKS_HOST` | Хост StarRocks | `localhost` |
| `STARROCKS_PORT` | Порт StarRocks | `9030` |
| `STARROCKS_DATABASE` | Имя базы данных | `autoorder_data` |
| `STARROCKS_USER` | Пользователь (из Docker Secrets) | `secretmagic` |
| `STARROCKS_PASSWORD` | Пароль (из Docker Secrets) | - |
| `STARROCKS_TIMEOUT` | Query timeout | `300s` |
| `STARROCKS_MAX_RETRIES` | Количество retry | `3` |

### Feature Engineering

| Переменная | Описание | Default |
|-----------|----------|---------|
| `FEATURE_WINDOW_DAYS` | Окно для расчёта фич (дней) | `90` |
| `FEATURE_MIN_SAMPLES` | Мин. кол-во сэмплов для фичи | `7` |
| `FEATURE_NAN_STRATEGY` | Стратегия NaN (decay/fill_zero/drop) | `decay` |
| `FEATURE_PARTITIONS` | Партиций для параллелизма | `4` |

### BOM Explosion

| Переменable | Описание | Default |
|-----------|----------|---------|
| `BOM_MAX_LEVELS` | Максимальная глубина BOM | `5` |
| `BOM_INCLUDE_PRODUCED_AT` | Учитывать produced_at | `true` |
| `BOM_CYCLE_DETECTION` | Детектировать циклы | `true` |

### Service

| Переменная | Описание | Default |
|-----------|----------|---------|
| `SERVICE_NAME` | Имя сервиса | `secretmagic` |
| `SERVICE_VERSION` | Версия сервиса | `0.1.0` |
| `ENVIRONMENT` | Окружение (dev/stage/prod) | `dev` |

### Server

| Переменная | Описание | Default |
|-----------|----------|---------|
| `HTTP_PORT` | HTTP порт | `8080` |
| `GRPC_PORT` | gRPC порт | `9000` |
| `TLS_ENABLED` | Включить TLS | `false` |
| `TLS_CERT_PATH` | Путь к TLS cert | - |
| `TLS_KEY_PATH` | Путь к TLS key | - |

### Logging

| Переменная | Описание | Default |
|-----------|----------|---------|
| `LOG_LEVEL` | Уровень логирования | `info` |
| `LOG_FORMAT` | Формат логов (json/text) | `json` |

## Docker Secrets

### MVP решение (текущее)

Создайте secrets в `/run/secrets/`:

```bash
# На хосте
echo "my_secure_password" | sudo tee /run/secrets/db_password
echo "starrocks_secure_password" | sudo tee /run/secrets/starrocks_password

# Права доступа
sudo chmod 600 /run/secrets/*
```

### Production (Kubernetes Secrets)

В Kubernetes secrets монтируются как volume:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secretmagic
spec:
  containers:
  - name: secretmagic
    volumeMounts:
    - name: secrets
      mountPath: /run/secrets
      readOnly: true
  volumes:
  - name: secrets
    secret:
      secretName: secretmagic-secrets
```

**Код остаётся тем же** - loader читает из `/run/secrets/`.

## Docker Compose

Пример `docker-compose.yml`:

```yaml
services:
  secretmagic:
    image: secretmagic:latest
    environment:
      # Database
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=secretmagic
      - DB_USER=secretmagic
      - DB_PASSWORD=${POSTGRES_PASSWORD:-secretmagic_dev_pass}

      # StarRocks
      - STARROCKS_HOST=starrocks
      - STARROCKS_PORT=9030
      - STARROCKS_DATABASE=autoorder_data
      - STARROCKS_USER=secretmagic
      - STARROCKS_PASSWORD=${STARROCKS_PASSWORD:-starrocks_dev_pass}

      # Service
      - SERVICE_NAME=secretmagic
      - SERVICE_VERSION=0.1.0
      - LOG_LEVEL=debug

      # Feature Engineering
      - FEATURE_WINDOW_DAYS=90
      - FEATURE_NAN_STRATEGY=decay

      # BOM Explosion
      - BOM_MAX_LEVELS=5

    secrets:
      - db_password
      - starrocks_password

secrets:
  db_password:
    file: /run/secrets/db_password
  starrocks_password:
    file: /run/secrets/starrocks_password
```

## Валидация

Конфигурация валидируется при загрузке:

### Обязательные параметры

- `SERVICE_NAME` не пустое
- `ENVIRONMENT` = `dev` | `stage` | `prod`
- `DB_HOST` не пустое
- `DB_PORT` в диапазоне 1-65535
- `DB_NAME` не пустое
- `DB_USER` не пустое
- `STARROCKS_HOST` не пустое

### Production-specific

В `production` обязательны:
- `DB_PASSWORD` (не может быть пустым)
- `STARROCKS_PASSWORD` (не может быть пустым)
- `TLS_ENABLED=true` с валидными путями к сертификатам

### Feature Engineering

- `FEATURE_WINDOW_DAYS` > 0 и ≤ 365
- `FEATURE_MIN_SAMPLES` > 0
- `FEATURE_NAN_STRATEGY` = `decay` | `fill_zero` | `drop`

### BOM Explosion

- `BOM_MAX_LEVELS` в диапазоне 1-10
- `BOM_INCLUDE_PRODUCED_AT` = `true` | `false`

### Logging

- `LOG_LEVEL` = `debug` | `info` | `warn` | `error`
- `LOG_FORMAT` = `json` | `text`

## Изменение конфигурации

### Статическая конфигурация (GlobalConfig)

Требует **перезапуска** приложения:

```bash
# 1. Изменить переменную окружения в docker-compose.yml
# 2. Перезапустить контейнер
docker compose restart secretmagic
```

### Динамическая конфигурация (Feature Engineering)

**Не требует** перезапуска - изменения в БД подхватываются автоматически:

```sql
-- Изменить окно для фич клиента
UPDATE feature_configs
SET window_days = 180
WHERE client_id = 'uuid-here';

-- Изменения подхватятся при следующем запуске job
```

## Multi-tenant routing

JobConfig определяет куда писать данные клиента в StarRocks. Режим определяется полем `tenant_mode` в таблице `clients`.

### prefixed_tables (дефолт)

**Назначение:** основной режим для 0-10,000 клиентов

```
Database: autoorder_data
Tables: c{organization_id}_features, c{organization_id}_bom, ...
```

**Пример:** Клиент с `organization_id = 2`:
- `autoorder_data.c2_features`
- `autoorder_data.c2_bom`
- `autoorder_data.c2_timeseries`

**Особенности:**
- Префикс `c{org_id}_` для изоляции данных
- Партиционирование по времени: `PARTITION BY date_trunc('MONTH', ts)`
- Простая миграция: `RENAME TABLE c2_features TO client_2.features`
- Миграции схемы: ALTER TABLE + blue/green deployment

### dedicated_db (крупные клиенты)

**Назначение:** клиенты с высокой нагрузкой или требованиями к изоляции

```
Database: client_{organization_id}
Tables: features, bom, timeseries, ...
```

**Пример:** Клиент с `organization_id = 2`:
- `client_2.features`
- `client_2.bom`

**Особенности:**
- Отдельная database для полной изоляции
- Возможность выделенных compute-ресурсов (workload groups/warehouses)
- Независимые бэкапы и миграции

**Триггеры апгрейда (SLO):**
- Объём данных (90 дней) > 300-500 GB
- Ingress > 50 MB/s стабильно или > 2 TB/день
- p95 latency > 2× медианы кластера 3 дня подряд
- Доля compute в workload group > 25-30%

### shared (опциональный)

**Назначение:** кросс-клиентская аналитика, не дефолт

```
Database: autoorder_data
Tables: features, bom (с полем tenant_id)
```

**Пример:**
- `autoorder_data.features` WHERE `tenant_id = 2`

**Особенности:**
- Минимальные метаданные (20 таблиц на все клиенты)
- Сложная миграция клиента (требует перепаковки партиций)
- Используется редко, для специфичных кейсов

## Troubleshooting

### Приложение не запускается

**Проблема:** `Failed to load configuration: invalid environment: test`

**Решение:** Проверьте `ENVIRONMENT`:
```bash
docker compose exec secretmagic env | grep ENVIRONMENT
# Должно быть: dev, stage или prod
```

### Не читает Docker Secret

**Проблема:** `database password is required in production`

**Решение:** Проверьте файл secret:
```bash
ls -la /run/secrets/db_password
cat /run/secrets/db_password
```

### StarRocks connection failed

**Проблема:** `Failed to connect to StarRocks: access denied`

**Решение:** Проверьте credentials:
```bash
ls -la /run/secrets/starrocks_password
cat /run/secrets/starrocks_password

# Проверьте подключение вручную
docker compose exec secretmagic python -c "
from src.database import get_starrocks_conn
conn = get_starrocks_conn()
print('Connection successful')
"
```

### TLS ошибки

**Проблема:** `TLS cert path is required when TLS is enabled`

**Решение:** Либо отключите TLS (`TLS_ENABLED=false`), либо укажите пути:
```bash
TLS_ENABLED=true
TLS_CERT_PATH=/app/certs/server.crt
TLS_KEY_PATH=/app/certs/server.key
```

### Feature engineering ошибки

**Проблема:** `ValueError: FEATURE_WINDOW_DAYS must be between 1 and 365`

**Решение:** Проверьте значение переменной:
```bash
docker compose exec secretmagic env | grep FEATURE_WINDOW_DAYS
# Должно быть: 1 ≤ значение ≤ 365
```
