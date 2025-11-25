"""
SecretMagic microservice - Feature Engineering & BOM Explosion

Event-driven consumer без HTTP/gRPC серверов.
Подписывается на события от integrator, обрабатывает данные, публикует результаты.
"""

import asyncio
import signal
import sys
from functools import partial

from src.config.settings import Settings
from src.database.postgres import PostgresClient
from src.events.client import RedisClient
from src.events.subscriber import EventSubscriber
from src.handlers.event_handler import EventHandler
from src.logger.logger import get_logger, init_logger
from src.logger.postgres_writer import PostgresWriter
from src.logger.types import Category, category, param
from src.repository.client_repository import ClientRepository


async def shutdown(
    redis_client: RedisClient,
    postgres_client: PostgresClient,
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

    # Initialize Redis client for event-driven communication
    redis_client = RedisClient(settings.redis)
    await redis_client.connect()

    logger.info(
        "Connected to messenger (Redis)",
        category(Category.MESSENGER),
        param("host", settings.redis.host),
        param("port", settings.redis.port),
    )

    # Initialize repositories
    client_repository = ClientRepository(postgres_client)

    # Initialize event handler
    event_handler = EventHandler(client_repository)

    # Initialize event subscriber (читаем события от integrator)
    subscriber = EventSubscriber(
        redis_client=redis_client,
        consumer_group=settings.redis.consumer_group,
        streams=settings.redis.subscribe_streams,
    )

    # Setup graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig: int) -> None:
        logger.info("Received signal", param("signal", sig))
        asyncio.create_task(shutdown(redis_client, postgres_client, subscriber, log_writer))
        loop.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, partial(signal_handler, sig))

    # Start consuming events
    try:
        logger.info(
            "Starting event consumer",
            category(Category.MESSENGER),
            param("consumer_group", settings.redis.consumer_group),
            param("streams", settings.redis.subscribe_streams),
        )
        await subscriber.consume(event_handler.handle)
    except Exception as e:
        logger.error("Fatal error in event consumer", e, param("error", str(e)))
        await shutdown(redis_client, postgres_client, subscriber, log_writer)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
