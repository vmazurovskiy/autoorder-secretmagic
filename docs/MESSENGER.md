# Messenger (Event-Driven Communication)

Система асинхронной коммуникации между микросервисами на основе Redis Streams для event-driven архитектуры.

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│              Integrator (upstream)                       │
│  - Публикует: sales_updated, stock_updated, bom_updated │
└─────────────────────────────────────────────────────────┘
                         │
                         │ публикует в
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Redis Streams                              │
│  stream: "sales-updates"   → sales_updated events       │
│  stream: "stock-updates"   → stock_updated events       │
│  stream: "bom-updates"     → bom_updated events         │
│  stream: "products-updates"→ products_updated events    │
└─────────────────────────────────────────────────────────┘
                         │
                         │ читает через XREADGROUP
                         ▼
┌─────────────────────────────────────────────────────────┐
│     SecretMagic (subscriber + publisher)                │
│  consumer_group: "secretmagic-group"                    │
│  - Подписывается на события от integrator               │
│  - Обрабатывает: feature engineering + BOM explosion    │
│  - Публикует свои события: features_updated             │
└─────────────────────────────────────────────────────────┘
                         │
                         │ публикует в
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Redis Streams                              │
│  stream: "features-updates" → features_updated events   │
│  stream: "bom-exploded"     → bom_exploded events       │
└─────────────────────────────────────────────────────────┘
                         │
                         │ читают через XREADGROUP
                         ▼
┌─────────────────────────────────────────────────────────┐
│     Downstream (trainer, inference, analytics)          │
│  consumer_group: "trainer-group", "analytics-group"     │
│  - Используют готовые ML-фичи из StarRocks              │
└─────────────────────────────────────────────────────────┘
```

## Поток событий

### 1. Конфигурация

**Immutable** (environment variables / Docker Secrets):
```bash
MESSENGER_HOST=redis
MESSENGER_PORT=6379
MESSENGER_PASSWORD=/run/secrets/redis_password
MESSENGER_DB=0
```

**Mutable** (configs/config.dev.yaml, hot-reload без перезапуска):
```yaml
messenger:
  subscriber:
    enabled: true                       # Включить/выключить подписку на события
    consumer_group: "secretmagic-group" # Consumer group для этого сервиса
    streams:
      - "sales-updates"                 # Подписываемся на события от integrator
      - "stock-updates"
      - "bom-updates"
      - "products-updates"

  publisher:
    enabled: true                       # Включить/выключить публикацию событий
    max_length: 10000                   # Retention: последние 10k событий
    streams:
      features_updated: "features-updates"     # Маппинг event_type → stream_name
      bom_exploded: "bom-exploded"
```

### 2. Инициализация (src/main.py)

```python
from src.events import MessengerClient, Publisher, Subscriber

# 1. Создаём Redis клиент
messenger_client = MessengerClient(
    host=cfg.messenger.host,          # из env: MESSENGER_HOST
    port=cfg.messenger.port,          # из env: MESSENGER_PORT
    password=cfg.messenger.password,  # из secret: redis_password
    db=cfg.messenger.db,              # из env: MESSENGER_DB
)

# 2. Создаём Subscriber для чтения событий от integrator
messenger_subscriber = Subscriber(
    client=messenger_client,
    consumer_group=cfg.mutable.messenger.subscriber.consumer_group,  # "secretmagic-group"
    streams=cfg.mutable.messenger.subscriber.streams,  # ["sales-updates", "stock-updates", ...]
    logger=app_logger,
)

# 3. Создаём Publisher для публикации своих событий
messenger_publisher = Publisher(
    client=messenger_client,
    streams=cfg.mutable.messenger.publisher.streams,   # маппинг event_type → stream
    max_len=cfg.mutable.messenger.publisher.max_length,  # 10000
    service_name="secretmagic",
    logger=app_logger,
)

# 4. Передаём в pipeline
pipeline = FeaturePipeline(
    subscriber=messenger_subscriber,
    publisher=messenger_publisher,
    logger=app_logger,
)
```

### 3. Обработка событий (src/pipeline/feature_pipeline.py)

```python
class FeaturePipeline:
    def __init__(self, subscriber: Subscriber, publisher: Publisher, logger: Logger):
        self.subscriber = subscriber
        self.publisher = publisher
        self.logger = logger

    async def run(self):
        """Основной цикл обработки событий."""
        while True:
            # 1. Читаем события из Redis Streams
            events = await self.subscriber.read_events(count=10, block=5000)

            for event in events:
                await self.process_event(event)

    async def process_event(self, event: Event):
        """Обработка одного события."""
        if event.event_type == "sales_updated":
            # 1. Прочитать данные из StarRocks по client_id
            client_id = event.client_id
            table_name = event.data.get("table_name")  # "sales"

            # 2. Выполнить feature engineering
            features_df = await self.feature_engineering.calculate_features(
                client_id=client_id,
                data_type=table_name,
            )

            # 3. Сохранить фичи в StarRocks
            await self.starrocks.write_features(client_id, features_df)

            # 4. Опубликовать событие о готовности фич
            await self.publish_features_updated(client_id)

        elif event.event_type == "bom_updated":
            # BOM explosion обработка
            await self.bom_explosion.process(event.client_id)
            await self.publish_bom_exploded(event.client_id)

    async def publish_features_updated(self, client_id: str):
        """Публикация события о готовности фич."""
        event = Event(
            event_type="features_updated",
            client_id=client_id,
            data={
                "features_count": 42,
                "processing_time_ms": 1234,
            },
        )
        await self.publisher.publish(event)
        # → Redis Stream: "features-updates"
        # → PostgreSQL logs: category='messenger'
```

### 4. Маппинг событий

**События, которые ЧИТАЕМ (от integrator):**

| EventType | Stream Name | Что делаем |
|-----------|-------------|-----------|
| `sales_updated` | `sales-updates` | Пересчитываем фичи на основе продаж |
| `stock_updated` | `stock-updates` | Пересчитываем фичи на основе остатков |
| `bom_updated` | `bom-updates` | Запускаем BOM explosion |
| `products_updated` | `products-updates` | Обновляем метаданные продуктов |

**События, которые ПУБЛИКУЕМ (downstream):**

| EventType | Stream Name | Когда публикуется |
|-----------|-------------|-------------------|
| `features_updated` | `features-updates` | После успешного feature engineering |
| `bom_exploded` | `bom-exploded` | После успешной BOM explosion |

## Типы событий

### Входящие события (от integrator)

```json
{
  "event_id": "uuid",
  "event_type": "sales_updated",
  "client_id": "client-uuid",
  "timestamp": "2025-11-22T14:00:00Z",
  "data": {
    "integration_id": "integration-uuid",
    "table_name": "sales"
  }
}
```

### Исходящие события (наши)

```json
{
  "event_id": "uuid",
  "event_type": "features_updated",
  "client_id": "client-uuid",
  "timestamp": "2025-11-22T14:05:00Z",
  "data": {
    "features_count": 42,
    "processing_time_ms": 1234,
    "feature_types": ["ema", "ma", "std", "lags", "seasonality"]
  }
}
```

**Event Notification Pattern:**
- Событие содержит минимум метаданных (уведомление)
- Подписчики читают полные данные из StarRocks по `client_id`

## Consumer Groups

**Зачем нужны:**
- Load balancing между инстансами ОДНОГО микросервиса
- Каждый микросервис имеет свою consumer group: `{service_name}-group`
- Разные сервисы независимо потребляют ВСЕ события

**Пример:**
```
Stream: "sales-updates" (100 событий)

Consumer Group: "secretmagic-group"
├─ secretmagic-instance-1  → читает события 1-50
└─ secretmagic-instance-2  → читает события 51-100

Consumer Group: "trainer-group"
├─ trainer-instance-1      → читает ВСЕ 100 событий
└─ trainer-instance-2      → (standby)
```

## Мониторинг

### Логи в PostgreSQL

```sql
-- События, обработанные за последние 10 минут
SELECT timestamp, message, context
FROM secretmagic.logs
WHERE category = 'messenger'
  AND timestamp > NOW() - INTERVAL '10 minutes'
ORDER BY timestamp DESC;

-- Ошибки обработки событий
SELECT timestamp, message, error, context
FROM secretmagic.logs
WHERE category = 'messenger'
  AND level = 'error'
ORDER BY timestamp DESC
LIMIT 20;
```

### Redis Streams (внутри контейнера)

```bash
# Подключиться к Redis
docker exec -it <redis_container_id> redis-cli

# Посмотреть список streams
KEYS *

# Длина stream
XLEN features-updates

# Последние 10 событий
XREVRANGE features-updates + - COUNT 10

# Информация о consumer groups
XINFO GROUPS sales-updates

# Pending сообщения (не подтверждённые)
XPENDING sales-updates secretmagic-group

# Отставание consumer group
XINFO GROUPS sales-updates
# Смотрим lag (разница между последним ID в stream и последним обработанным)
```

## Отключение messenger

**Временное отключение подписки (без перезапуска):**
```yaml
# configs/config.dev.yaml
messenger:
  subscriber:
    enabled: false  # Отключить чтение событий
```

**Временное отключение публикации (без перезапуска):**
```yaml
messenger:
  publisher:
    enabled: false  # Отключить публикацию событий
```

**Полное отключение (требует перезапуск):**
```bash
# Не устанавливать переменные окружения
# Subscriber и Publisher будут None, обработка автоматически пропускается
```

## Graceful Shutdown

```python
# src/main.py
async def shutdown():
    """Graceful shutdown приложения."""
    # 1. Остановить чтение новых событий
    await messenger_subscriber.stop()

    # 2. Дождаться завершения обработки текущих событий
    await pipeline.wait_for_completion()

    # 3. Закрыть соединение с Redis
    await messenger_client.close()

    logger.info("Messenger shutdown completed")

# Регистрация graceful shutdown
signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)
```

## Retry и Error Handling

```python
class FeaturePipeline:
    async def process_event(self, event: Event):
        """Обработка события с retry."""
        try:
            # Обработка события
            await self._process_event_internal(event)

            # Подтверждаем успешную обработку (ACK)
            await self.subscriber.ack(event)

        except RetryableError as e:
            # Повторяем обработку позже (не ACK)
            self.logger.warning(f"Retryable error: {e}, event will be reprocessed")

        except FatalError as e:
            # Критичная ошибка → ACK чтобы не блокировать очередь
            self.logger.error(f"Fatal error: {e}, skipping event")
            await self.subscriber.ack(event)

            # Сохраняем в DLQ (Dead Letter Queue) для ручного разбора
            await self.dlq.push(event, error=str(e))
```

## Архитектурные принципы

1. **Fail-safe:** Если messenger недоступен, обработка продолжает работать (события не читаются/публикуются)
2. **Event Notification Pattern:** События содержат минимум данных, подписчики читают из StarRocks
3. **Variant A (stream by event type):** Каждый тип данных → отдельный stream (масштабируемость)
4. **Hot-reload:** Маппинг streams обновляется из config.yaml без перезапуска
5. **Dual logging:** Redis Streams (real-time) + PostgreSQL logs (debugging)
6. **At-least-once delivery:** Consumer groups гарантируют доставку минимум 1 раз (идемпотентность обработки обязательна)

## См. также

- [CONFIGURATION.md](CONFIGURATION.md) - Двухуровневая система конфигурации
- [DATABASE_METADATA.md](DATABASE_METADATA.md) - База данных метаданных
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Общая архитектура микросервиса
