"""
SecretMagic microservice - Feature Engineering & BOM Explosion

Event-driven consumer без HTTP/gRPC серверов.
Подписывается на события от integrator, обрабатывает данные, публикует результаты.
"""

import asyncio
import contextlib
import signal
from functools import partial
from typing import Any

from src.config.settings import Settings
from src.database.postgres import PostgresClient
from src.database.starrocks import StarRocksClient
from src.events.client import RedisClient
from src.events.subscriber import EventSubscriber
from src.features.calendar import CalendarBuilder, CalendarConfig
from src.features.sales import SalesFeatureProcessor
from src.handlers.event_handler import EventHandler
from src.logger.logger import get_logger, init_logger
from src.logger.postgres_writer import PostgresWriter
from src.logger.types import Category, category, param
from src.repository.calendar_repository import CalendarRepository
from src.repository.client_repository import ClientRepository
from src.repository.config_repository import ConfigRepository
from src.repository.processing_repository import ProcessingRepository


async def ensure_calendar_updated(
    config_repo: ConfigRepository,
    calendar_repo: CalendarRepository,
    logger: Any,  # noqa: ANN401
) -> None:
    """
    Check and update dim_calendar if needed.

    Logic:
    1. If dim_calendar is empty -> full load from start_date
    2. If today >= future_upload date and next year not loaded -> load next year
    """
    from datetime import date, datetime

    # Get config values
    start_date = config_repo.get_date(
        "calendar_start_date",
        default=date(2020, 1, 1),
    )
    future_upload = config_repo.get_day_month("calendar_future_upload")
    region = config_repo.get_value("calendar_region", default="ru")

    # Ensure table exists (create if not)
    if not calendar_repo.ensure_table_exists():
        logger.error(
            "Failed to ensure dim_calendar table exists",
            category(Category.STARROCKS),
        )
        return

    # Get current max date in calendar
    current_max_date = calendar_repo.get_max_date()

    today = datetime.utcnow().date()
    current_year = today.year

    # Determine target end date
    if current_max_date is None:
        # Empty table - full load
        target_date = date(current_year, 12, 31)
        logger.info(
            "dim_calendar is empty, will create full calendar",
            category(Category.STARROCKS),
            param("from", str(start_date)),
            param("to", str(target_date)),
        )
    elif future_upload:
        # Check if we need to load next year
        upload_day, upload_month = future_upload
        upload_trigger = date(current_year, upload_month, upload_day)
        next_year_end = date(current_year + 1, 12, 31)

        if today >= upload_trigger and current_max_date < next_year_end:
            target_date = next_year_end
            logger.info(
                "Loading next year calendar (future_upload triggered)",
                category(Category.STARROCKS),
                param("trigger_date", str(upload_trigger)),
                param("current_max", str(current_max_date)),
                param("new_target", str(target_date)),
            )
        elif current_max_date < date(current_year, 12, 31):
            target_date = date(current_year, 12, 31)
            logger.info(
                "Completing current year calendar",
                category(Category.STARROCKS),
                param("current_max", str(current_max_date)),
                param("new_target", str(target_date)),
            )
        else:
            logger.info(
                "dim_calendar is up to date",
                category(Category.STARROCKS),
                param("max_date", str(current_max_date)),
            )
            return
    else:
        # No future_upload config - just ensure current year
        if current_max_date >= date(current_year, 12, 31):
            logger.info(
                "dim_calendar is up to date",
                category(Category.STARROCKS),
                param("max_date", str(current_max_date)),
            )
            return
        target_date = date(current_year, 12, 31)

    # Build and insert calendar
    config = CalendarConfig(
        region=region or "ru",
        start_date=start_date or date(2020, 1, 1),
    )
    builder = CalendarBuilder(config)
    calendar_df = builder.build(date_from=start_date, date_to=target_date)

    # Upsert to StarRocks
    rows_inserted = calendar_repo.upsert_dataframe(calendar_df)

    logger.info(
        "dim_calendar updated",
        category(Category.STARROCKS),
        param("rows", rows_inserted),
        param("columns", len(calendar_df.columns)),
        param("date_from", str(start_date)),
        param("date_to", str(target_date)),
    )


async def shutdown(
    redis_client: RedisClient,
    postgres_client: PostgresClient,
    starrocks_client: StarRocksClient,
    subscriber: EventSubscriber,
    log_writer: PostgresWriter,
) -> None:
    """Graceful shutdown."""
    logger = get_logger()
    logger.info("Shutting down SecretMagic...")

    # 1. Остановить чтение новых событий
    await subscriber.stop()

    # 2. Закрыть соединения
    await redis_client.close()
    await starrocks_client.close()
    await postgres_client.close()

    # 3. Закрыть log writer (flush оставшихся логов)
    await log_writer.close()

    logger.info("Shutdown complete")


async def main() -> None:
    """Main entry point."""
    # Load settings
    settings = Settings()

    # Initialize PostgreSQL writer for logs
    log_writer = PostgresWriter(
        dsn=settings.postgres.dsn,
        batch_size=100,
        flush_interval=5.0,
    )
    await log_writer.connect()

    # Initialize logger
    init_logger(
        service_name=settings.service_name,
        environment=settings.environment,
        writer=log_writer,
    )
    logger = get_logger()

    logger.info(
        "Starting SecretMagic",
        param("environment", settings.environment),
        param("service_name", settings.service_name),
        param("version", settings.service_version),
    )

    # Initialize database clients
    postgres_client = PostgresClient(settings.postgres)
    await postgres_client.connect()
    logger.info("Connected to PostgreSQL", category(Category.DATABASE))

    # Initialize StarRocks client (аналитическая БД)
    starrocks_client = StarRocksClient(settings.starrocks)
    await starrocks_client.connect()
    logger.info(
        "Connected to StarRocks",
        category(Category.STARROCKS),
        param("host", settings.starrocks.host),
        param("database", settings.starrocks.database),
    )

    # Initialize repositories
    client_repository = ClientRepository(postgres_client)
    processing_repository = ProcessingRepository(postgres_client)
    config_repository = ConfigRepository(postgres_client)
    calendar_repository = CalendarRepository(starrocks_client)

    # Initialize and update dim_calendar if needed
    await ensure_calendar_updated(config_repository, calendar_repository, logger)

    # Initialize feature processors
    sales_processor = SalesFeatureProcessor(starrocks_client, processing_repository)
    logger.info("SalesFeatureProcessor initialized", category(Category.STARROCKS))

    # Initialize event handler
    event_handler = EventHandler(client_repository, sales_processor)

    # Initialize Redis client (connection deferred until after healthcheck)
    redis_client = RedisClient(settings.redis)

    # Initialize event subscriber
    subscriber = EventSubscriber(
        redis_client=redis_client,
        consumer_group=settings.redis.consumer_group,
        streams=settings.redis.subscribe_streams,
    )

    # Setup graceful shutdown
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler(sig: int) -> None:
        logger.info("Received signal", param("signal", sig))
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, partial(signal_handler, sig))

    # Application started - healthcheck will pass now (python is running)
    logger.info(
        "SecretMagic ready, waiting for network initialization...",
        param("consumer_group", settings.redis.consumer_group),
        param("streams", settings.redis.subscribe_streams),
    )

    # Wait for Docker Swarm overlay network to fully attach
    # This prevents DNS resolution failures due to network race conditions
    await asyncio.sleep(15)

    # Now connect to Redis
    await redis_client.connect()

    logger.info(
        "Connected to messenger (Redis)",
        category(Category.MESSENGER),
        param("host", settings.redis.host),
        param("port", settings.redis.port),
    )

    # Start consuming events
    try:
        logger.info("Starting event consumer", category(Category.MESSENGER))

        # Запускаем consumer и ожидание сигнала параллельно
        consumer_task = asyncio.create_task(subscriber.consume(event_handler.handle))
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        # Ждём либо завершения consumer, либо сигнала shutdown
        done, pending = await asyncio.wait(
            [consumer_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Отменяем pending задачи
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    except Exception as e:
        logger.error("Fatal error in event consumer", e, param("error", str(e)))
    finally:
        await shutdown(redis_client, postgres_client, starrocks_client, subscriber, log_writer)


if __name__ == "__main__":
    asyncio.run(main())
