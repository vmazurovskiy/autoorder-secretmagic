# CLAUDE.md - SecretMagic Microservice

## 📋 ОБЗОР

**SecretMagic** — ключевой микросервис в экосистеме AutoOrder Platform. Отвечает за подготовку данных для ML: feature engineering, BOM-explosion, обработку временных рядов, учёт сезонности, погоды и промо-акций.

### 🎯 ОСНОВНАЯ ЗАДАЧА

Трансформировать нормализованные данные от `integrator` в качественные ML-фичи, выполнить декомпозицию техкарт (BOM-explosion) и подготовить данные для `trainer` (обучение) и `inference` (прогнозирование).

---

## 📖 ДОКУМЕНТАЦИЯ

### Обязательное чтение:

1. **[README.md](README.md)** - описание проекта, быстрый старт, структура
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - подробная архитектура микросервиса
3. **[docs/CHANGELOG.md](docs/CHANGELOG.md)** - история изменений и версий
4. **[../CLAUDE.md](../CLAUDE.md)** - общие принципы для всех микросервисов
5. **[../ARCHITECTURE.md](../ARCHITECTURE.md)** - общая архитектура платформы

### Детальная документация (docs/):

- **[docs/MESSENGER.md](docs/MESSENGER.md)** - event-driven коммуникация через Redis Streams
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** - система конфигурации
- **[docs/DATABASE_METADATA.md](docs/DATABASE_METADATA.md)** - база данных метаданных (PostgreSQL)
- **[docs/CI_CD.md](docs/CI_CD.md)** - CI/CD pipeline (GitHub Actions + Docker Swarm)
- **[docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md)** - процесс релизов и версионирование

---

## 🚫 СТРОГИЕ ЗАПРЕТЫ

- ❌ **НЕ запускать команды в фоновом режиме** (background) без явного подтверждения пользователя
- ❌ **НЕ использовать `run_in_background: true`** в Bash tool без разрешения
- ❌ **НЕ запускать код или сервисы** без явной команды пользователя

---

## 🔄 CI/CD И GIT WORKFLOW

### Структура веток

- **`develop`** - основная ветка разработки (DEV окружение)
- **`master`** - production ветка (PROD окружение)
- **`feature/*`** - ветки для новых фич (создаются от develop)
- **`fix/*`** - ветки для исправлений багов (создаются от develop)
- **`hotfix/*`** - критичные исправления для PROD (создаются от master, мержатся в master И develop)

### Правила работы с ветками

#### ❌ ЗАПРЕЩЕНО:

- Пушить напрямую в `develop` или `master`
- Мержить без code review
- Коммитить `__pycache__/`, `*.pyc`, `.venv/`, `.pytest_cache/`, `.mypy_cache/`

#### ✅ ОБЯЗАТЕЛЬНО:

1. **Создать feature ветку:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Сделать коммиты:**
   ```bash
   git add <files>
   git commit -m "feat: description"  # Используй Conventional Commits
   git push origin feature/your-feature-name
   ```

3. **Создать Pull Request:**
   - GitHub → Pull Requests → New Pull Request
   - Base: `develop` ← Compare: `feature/your-feature-name`
   - Описать изменения
   - Дождаться code review

4. **После одобрения:**
   - Тим лид мержит PR в develop
   - CI/CD автоматически запустится

### Hotfix workflow (критичные исправления PROD)

**Когда использовать:** Критичный баг в production, требующий немедленного исправления.

1. **Создать hotfix ветку от master:**
   ```bash
   git checkout master
   git pull origin master
   git checkout -b hotfix/critical-bug-fix
   ```

2. **Исправить баг и закоммитить:**
   ```bash
   git add <files>
   git commit -m "hotfix: fix critical bug in production"
   git push origin hotfix/critical-bug-fix
   ```

3. **Создать PR в master:**
   - Base: `master` ← Compare: `hotfix/critical-bug-fix`
   - Пометить как `urgent`

4. **После мерджа в master:**
   - Автоматически деплоится в PROD
   - **КРИТИЧНО:** Обратный мердж hotfix в develop!
   ```bash
   git checkout develop
   git pull origin develop
   git merge hotfix/critical-bug-fix
   git push origin develop
   ```

### CI/CD Triggers

#### DEV окружение (автоматически):

```yaml
Trigger: push в develop или master
Exclude: docs/**, *.md, .gitignore, LICENSE
```

**Что происходит:**
1. CI запускает линтер (ruff, mypy) + тесты (pytest)
2. Собирает Docker образ `dev-{SHORT_SHA}`
3. Пушит в registry `cr.selcloud.ru/autoorder-platform/secretmagic`
4. Деплоит в DEV Swarm (автоматически)

**Время:** ~3-5 минут от push до deploy

#### STAGE окружение (вручную):

- Создать тег: `git tag stage-v1.2.3 && git push origin stage-v1.2.3`
- Или через GitHub Actions → Run workflow

#### PROD окружение (вручную + approval):

- Создать тег: `git tag v1.2.3 && git push origin v1.2.3`
- Manual approval required

### Conventional Commits

**Используй префиксы:**

- `feat:` - новая функциональность
- `fix:` - исправление бага
- `refactor:` - рефакторинг без изменения функциональности
- `docs:` - обновление документации
- `test:` - добавление/изменение тестов
- `chore:` - вспомогательные изменения (deps, configs)

**Примеры:**
```bash
git commit -m "feat: add exponential moving average features"
git commit -m "fix: handle NaN values in BOM explosion"
git commit -m "docs: update feature engineering pipeline"
```

### Проверка перед коммитом

**ОБЯЗАТЕЛЬНО:** Все проверки должны пройти успешно перед push в develop/master!

```bash
# Полная проверка (рекомендуется перед push)
make check

# Или по отдельности:

# 1. Форматирование (автоисправление)
make fmt  # ruff format .

# 2. Импорты (сортировка)
make isort  # ruff check --select I --fix .

# 3. Линтер (проверка качества кода)
make lint  # ruff check . && mypy .

# 4. Тесты (unit + integration)
make test  # pytest tests/

# 5. Проверка типов
make typecheck  # mypy src/
```

**Автоматизация через Git Hooks:**

```bash
# Установить pre-commit hook (рекомендуется)
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
set -e

echo "Running pre-commit checks..."

# Форматирование
make fmt

# Импорты
make isort

# Линтер
make lint

# Тесты
make test

echo "✅ Pre-commit checks passed"
EOF

chmod +x .git/hooks/pre-commit
```

**CI/CD автоматически блокирует:**
- ❌ Код с ошибками линтера (ruff, mypy)
- ❌ Код с провалившимися тестами (pytest)
- ❌ Код с ошибками типизации (mypy)

### Мониторинг CI/CD

```bash
# Проверить статус последнего workflow
gh run list --workflow=cd-dev.yml --limit 1

# Посмотреть логи workflow
gh run view <RUN_ID> --log

# Проверить деплой в DEV
docker service ps secretmagic-dev_secretmagic
```

### Откат (Rollback)

**Если DEV сломан после деплоя:**

```bash
# 1. Найти предыдущий образ
docker service ps secretmagic-dev_secretmagic --no-trunc

# 2. Откатиться на предыдущий образ
IMAGE="cr.selcloud.ru/autoorder-platform/secretmagic:dev-<PREVIOUS_SHA>"
docker service update --image $IMAGE secretmagic-dev_secretmagic

# 3. Или откатить Git
git revert <BAD_COMMIT_SHA>
git push origin develop  # Автоматически задеплоится
```

---

## 🔍 ОТЛАДКА

### Просмотр логов

**ВАЖНО:** Для просмотра логов использовать таблицу `secretmagic.logs` в PostgreSQL:

```sql
SELECT timestamp, level, message, error, context
FROM secretmagic.logs
WHERE timestamp > NOW() - INTERVAL '10 minutes'
ORDER BY timestamp DESC
LIMIT 50;
```

### Подключение к базам данных

**КРИТИЧНО:** На хосте нет SQL-клиентов. Все запросы к БД выполняются **через Docker контейнеры**.

#### PostgreSQL (метаданные, логи, конфигурации)

**Окружения:**
- DEV: `secretmagic-dev_postgres`
- STAGE: `secretmagic-stage_postgres`
- PROD: `secretmagic-prod_postgres`

**Учётные данные:** Секреты в `/run/secrets/` внутри контейнера secretmagic
- User: `secretmagic`
- Password: `/run/secrets/db_password`
- Database: `secretmagic`

```bash
# Найти контейнер PostgreSQL для DEV
docker ps -f name=secretmagic-dev_postgres

# Выполнить SQL запрос
docker exec <POSTGRES_CONTAINER_ID> psql -U secretmagic -d secretmagic \
  -c "SELECT * FROM secretmagic.clients LIMIT 5;"

# Интерактивная сессия
docker exec -it <POSTGRES_CONTAINER_ID> psql -U secretmagic -d secretmagic
```

**Примеры запросов:**
```sql
-- Просмотр логов
SELECT timestamp, level, message, error
FROM secretmagic.logs
ORDER BY timestamp DESC LIMIT 20;

-- Список клиентов
SELECT id, name, status FROM secretmagic.clients;

-- Конфигурации feature engineering
SELECT * FROM secretmagic.feature_configs WHERE active = true;
```

#### StarRocks (аналитические данные, временные ряды)

**ВАЖНО:** Каждое окружение имеет **изолированный** кластер StarRocks.

**Окружения:**
- DEV: `bigdatadb-dev_starrocks`
- STAGE: `bigdatadb-stage_starrocks`
- PROD: `bigdatadb-prod_starrocks`

**Учётные данные:** Секреты в `/run/secrets/` внутри контейнера secretmagic
- User: `/run/secrets/starrocks_user` (для secretmagic: `secretmagic`)
- Password: `/run/secrets/starrocks_password`
- Database: `autoorder_data`

**Через Python (из контейнера secretmagic)**

```bash
# Найти контейнер secretmagic для DEV
SECRETMAGIC_ID=$(docker ps -qf name=secretmagic-dev_secretmagic)

# Показать таблицы
docker exec $SECRETMAGIC_ID python -c "
from src.database import get_starrocks_conn
conn = get_starrocks_conn()
cursor = conn.cursor()
cursor.execute('SHOW TABLES FROM autoorder_data')
for row in cursor.fetchall():
    print(row)
"

# Проверка фич в StarRocks
docker exec $SECRETMAGIC_ID python -c "
from src.database import get_starrocks_conn
conn = get_starrocks_conn()
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM autoorder_data.features')
print(f'Total features: {cursor.fetchone()[0]}')
"
```

**ВАЖНО:**
- ✅ Используем **SQLAlchemy** + **pymysql** для работы с StarRocks
- ✅ Автоматически читает креды из `/run/secrets/`
- ✅ Connection pooling для оптимальной производительности
- ✅ Используем **Polars** для работы с большими датасетами
- ⚠️ Pandas для legacy совместимости

---

## 🛠️ ТЕХНОЛОГИЧЕСКИЙ СТЕК

- **Язык**: Python 3.12+
- **Фреймворки**: FastAPI (API), Polars/Pandas (обработка данных), NumPy/SciPy (вычисления)
- **БД**: PostgreSQL (конфигурации, логи), StarRocks 4.0+ (аналитика, временные ряды)
- **Storage**: Selectel S3 (промежуточные результаты, модели)
- **Messaging**: Messenger (Redis Streams) - event-driven коммуникация
- **ML**: scikit-learn, statsmodels (feature engineering), готовность к интеграции с AutoGluon
- **Тестирование**: pytest, pytest-cov, pytest-asyncio
- **Линтеры**: ruff (fast linter), mypy (type checking)

---

## 🏗️ КЛЮЧЕВЫЕ КОМПОНЕНТЫ

### 1. Feature Engineering Pipeline (`src/features/`)

Создание ML-фич из нормализованных данных:
- `time_series.py` - временные ряды (EMA, MA, STD, лаги)
- `seasonality.py` - сезонность (день недели, месяц, праздники)
- `weather.py` - погодные факторы
- `promo.py` - промо-акции и их влияние
- `calendar.py` - календарные признаки (выходные, праздники)

**Принципы:**
- Векторизованные операции через Polars/Pandas
- Обработка NaN с явной семантикой (decay vs missing data)
- Партиционирование по годам для масштабируемости
- Lazy evaluation где возможно (Polars)

### 2. BOM Explosion Engine (`src/bom/`)

Декомпозиция техкарт (Bill of Materials):
```
Блюдо → Полуфабрикаты → Сырьё
Рамен → Бульон + Лапша → Кости + Специи + Мука
```

**Возможности:**
- Многоуровневая декомпозиция (bom_lvl2)
- Учёт `produced_at` для производственных цепочек
- Расчёт таблиц обеспеченности
- Рекурсивная explosion с детекцией циклов

### 3. Event Handlers (`src/handlers/`)

Обработка событий от messenger (Redis Streams):
```
clients_updated → ClientRepository.upsert()
sales_updated → FeatureEngineeringPipeline.process()
stock_updated → InventoryPipeline.process()
bom_updated → BOMExplosion.explode()
```

**Data Flow:**
```
integrator → StarRocks (normalized data)
    ↓
SecretMagic (Feature Engineering + BOM Explosion)
    ↓
StarRocks (ML features) → trainer / inference
```

---

## ⚡ ПРАВИЛА РАЗРАБОТКИ

### Перед добавлением новой фичи:

1. **Определить тип фичи** - past covariates, known covariates, static
2. **Документировать в коде** - docstring с описанием семантики и NaN handling
3. **Написать тесты** (≥75% покрытие)
4. **Добавить в конфигурацию** - `configs/features.yaml`
5. **Обновить документацию** - `docs/FEATURE_ENGINEERING.md`

### Структура фичи:

```python
from typing import Optional
import polars as pl

def calculate_feature(
    df: pl.DataFrame,
    *,
    window_size: int = 7,
    min_samples: int = 1
) -> pl.DataFrame:
    """
    Calculate feature with explicit NaN handling.

    Args:
        df: Input DataFrame with 'series_id', 'timestamp', 'target'
        window_size: Rolling window size
        min_samples: Minimum samples required

    Returns:
        DataFrame with added feature column

    NaN Semantics:
        - Input NaN → filled with 0 for rolling (decay behavior)
        - Output < threshold → NaN (dead product signal)
    """
    return df.with_columns([
        pl.col('target')
          .fill_null(0)
          .rolling_mean(window_size, min_samples)
          .over('series_id')
          .alias('feature_name')
    ])
```

---

## 🧪 ТЕСТИРОВАНИЕ

### Запуск тестов:

```bash
make test              # Все тесты
make test-unit         # Unit тесты
make test-integration  # Integration тесты
make test-coverage     # С отчётом о покрытии
```

### Структура тестов:

```
tests/
├── unit/              # Unit тесты
│   ├── test_features.py
│   ├── test_bom.py
│   └── test_pipeline.py
├── integration/       # Integration тесты
│   ├── test_starrocks.py
│   └── test_full_pipeline.py
└── fixtures/          # Тестовые данные
    ├── sales_data.parquet
    ├── bom_data.json
    └── expected_features.parquet
```

### Требования:

- ✅ Все фичи покрыты unit-тестами
- ✅ Интеграционные тесты для каждого pipeline
- ✅ Моки для БД (pytest fixtures)
- ✅ Тестовые данные в `tests/fixtures/`
- ✅ Покрытие ≥75%

---

## 🚀 ЛОКАЛЬНАЯ РАЗРАБОТКА

### Быстрый старт:

```bash
# Создать виртуальное окружение
python3.12 -m venv .venv
source .venv/bin/activate

# Установка зависимостей
make deps  # pip install -r requirements.txt

# Проверка
make check

# Запуск
make run
```

### Docker:

```bash
# Сборка образа
make docker-build

# Запуск контейнера
make docker-run

# Проверка здоровья
curl http://localhost:8080/health
```

---

## 🌍 ДЕПЛОЙ ОКРУЖЕНИЙ

### Разделение окружений

Микросервис поддерживает полностью изолированные окружения с отдельными БД, сетями и конфигурациями:

| Окружение | Stack Name | БД | Сеть | Назначение |
|-----------|------------|----|----|------------|
| **DEV** | `secretmagic-dev` | `/srv/storage/autoorder/secretmagic-dev/postgres` | `autoorder-net-dev` | Разработка и тестирование |
| **STAGE** | `secretmagic-stage` | `/srv/storage/autoorder/secretmagic-stage/postgres` | `autoorder-net-stage` | Pre-production тесты |
| **PROD** | `secretmagic-prod` | `/srv/storage/autoorder/secretmagic-prod/postgres` | `autoorder-net-prod` | Production окружение |

### Сетевая инфраструктура (DEV)

| IP | Hostname | Роль | Сервисы |
|----|----------|------|---------|
| **10.77.0.1** | - | Swarm Manager | integrator, messenger, другие микросервисы |
| **10.77.0.2** | lde-gpu | Worker | **secretmagic** (текущая ВМ для разработки) |
| **10.77.0.3** | - | CI/CD Runner | GitHub Actions runner |

**Примечания:**
- Секретмагия запускается на worker-ноде `lde-gpu` (10.77.0.2)
- Для доступа к другим сервисам (integrator, messenger) используйте `ssh 10.77.0.1`
- CI/CD пайплайн выполняется на 10.77.0.3 и деплоит через Swarm Manager (10.77.0.1)

### Деплой DEV

```bash
ENVIRONMENT=dev \
POSTGRES_PASSWORD=secretmagic_dev_pass \
STARROCKS_PASSWORD=autoorder_secure_password \
docker stack deploy -c docker-compose.yml secretmagic-dev
```

### Деплой STAGE

```bash
ENVIRONMENT=stage \
POSTGRES_PASSWORD=${STAGE_POSTGRES_PASSWORD} \
STARROCKS_PASSWORD=${STAGE_STARROCKS_PASSWORD} \
docker stack deploy -c docker-compose.yml secretmagic-stage
```

### Деплой PROD

```bash
ENVIRONMENT=prod \
POSTGRES_PASSWORD=${PROD_POSTGRES_PASSWORD} \
STARROCKS_PASSWORD=${PROD_STARROCKS_PASSWORD} \
VERSION=v1.2.0 \
docker stack deploy -c docker-compose.yml secretmagic-prod
```

**ВАЖНО для PROD:**
- ✅ Всегда используйте версионированный образ (не `latest`)
- ✅ Храните секреты в переменных окружения или Vault
- ✅ Проверьте наличие всех обязательных переменных перед деплоем

### Проверка деплоя

```bash
# Проверка статуса stack
docker stack ps secretmagic-prod

# Проверка логов
docker service logs secretmagic-prod_secretmagic --tail 50

# Проверка здоровья
curl http://localhost:8080/health  # Изнутри сети
```

---

## 📊 API

### HTTP endpoints:

- `GET /health` - health check
- `GET /ready` - readiness probe
- `GET /metrics` - Prometheus метрики
- `POST /api/v1/features/process` - запуск feature engineering pipeline
- `POST /api/v1/bom/explode` - запуск BOM explosion

**Подробности**: см. [docs/API.md](docs/API.md)

---

## 📈 МЕТРИКИ

### Prometheus метрики:

- `secretmagic_features_processed_total` - количество обработанных фич
- `secretmagic_bom_explosion_duration_seconds` - время BOM explosion
- `secretmagic_pipeline_duration_seconds` - время полного pipeline
- `secretmagic_errors_total{type}` - количество ошибок по типам
- `secretmagic_nan_values_total{feature}` - количество NaN в фичах

### Трассировка:

OpenTelemetry trace ID прокидывается через все вызовы.

---

## ⚠️ ЧАСТЫЕ ОШИБКИ

### 1. NaN в фичах

**Проблема**: Неожиданные NaN значения в выходных фичах

**Решение**: Проверьте семантику NaN в документации фичи (decay vs missing data)

### 2. Циклические зависимости в BOM

**Проблема**: `BOMCyclicDependencyError` при explosion

**Решение**: Проверьте техкарты на циклические ссылки (A → B → C → A)

### 3. Out of memory при обработке больших датасетов

**Проблема**: OOM при обработке больших временных рядов

**Решение**: Используйте партиционирование по годам + Polars lazy evaluation

---

## 📝 ЧЕКЛИСТ

### Перед началом разработки:

- [ ] Прочитал [README.md](README.md)
- [ ] Прочитал [ARCHITECTURE.md](ARCHITECTURE.md)
- [ ] Понял роль SecretMagic в общей архитектуре
- [ ] Изучил существующие фичи в `src/features/`
- [ ] Запустил существующие тесты

### Перед коммитом:

- [ ] Тесты проходят (`make test`)
- [ ] Код отформатирован (`make fmt`)
- [ ] Линтер не выдаёт ошибок (`make lint`)
- [ ] Типы проверены (`make typecheck`)
- [ ] Документация обновлена (если нужно)

### Перед созданием PR:

- [ ] Покрытие тестами ≥75% (`make test-coverage`)
- [ ] Integration тесты добавлены
- [ ] FEATURE_ENGINEERING.md обновлён (для новых фич)
- [ ] Добавлены примеры использования в docstrings

---

## 🆘 ПОМОЩЬ

### При возникновении вопросов:

1. Проверьте [ARCHITECTURE.md](ARCHITECTURE.md) - детальная документация
2. Изучите документацию в `docs/`:
   - [MESSENGER.md](docs/MESSENGER.md) - работа с событиями
   - [DATABASE_METADATA.md](docs/DATABASE_METADATA.md) - схема БД и запросы
   - [CONFIGURATION.md](docs/CONFIGURATION.md) - настройка конфигурации
3. Изучите существующие фичи в `src/features/`
4. Посмотрите тесты в `tests/` - примеры использования
5. Проверьте [общий CLAUDE.md](../CLAUDE.md) - стандарты платформы

---

**Документация актуальна на:** 2025-11-26
