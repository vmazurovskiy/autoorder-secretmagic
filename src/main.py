"""
SecretMagic microservice - Feature Engineering & BOM Explosion

Event-driven consumer без HTTP/gRPC серверов.
Подписывается на события от integrator, обрабатывает данные, публикует результаты.
"""

import asyncio
import signal
import sys
from functools import partial

import structlog

from src.config.settings import Settings
from src.database.postgres import PostgresClient
from src.events.client import RedisClient
from src.events.publisher import EventPublisher
from src.events.subscriber import EventSubscriber
from src.pipeline.processor import EventProcessor

logger = structlog.get_logger()


async def shutdown(
    redis_client: RedisClient,
    postgres_client: PostgresClient,
    subscriber: EventSubscriber,
) -> None:
    """Graceful shutdown."""
    logger.info("Shutting down SecretMagic...")

    # 1. Остановить чтение новых событий
    await subscriber.stop()

    # 2. Закрыть соединения
    await redis_client.close()
    await postgres_client.close()

    logger.info("Shutdown complete")


async def main() -> None:
    """Main entry point."""
    # Load settings
    settings = Settings()

    logger.info(
        "Starting SecretMagic",
        environment=settings.environment,
        service_name=settings.service_name,
        version=settings.service_version,
    )

    # Initialize database clients
    postgres_client = PostgresClient(settings.postgres)
    await postgres_client.connect()

    # Initialize Redis client for event-driven communication
    redis_client = RedisClient(settings.redis)
    await redis_client.connect()

    # Initialize event subscriber (читаем события от integrator)
    subscriber = EventSubscriber(
        redis_client=redis_client,
        consumer_group=settings.redis.consumer_group,
        streams=settings.redis.subscribe_streams,
    )

    # Initialize event publisher (публикуем свои события)
    publisher = EventPublisher(
        redis_client=redis_client,
        streams_mapping=settings.redis.publish_streams,
    )

    # Initialize event processor
    processor = EventProcessor(
        postgres=postgres_client,
        publisher=publisher,
        settings=settings,
    )

    # Setup graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig: int) -> None:
        logger.info("Received signal", signal=sig)
        asyncio.create_task(shutdown(redis_client, postgres_client, subscriber))
        loop.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, partial(signal_handler, sig))

    # Start consuming events
    try:
        await subscriber.consume(processor.process_event)
    except Exception as e:
        logger.error("Fatal error in event consumer", error=str(e), exc_info=True)
        await shutdown(redis_client, postgres_client, subscriber)
        sys.exit(1)


if __name__ == "__main__":
    import logging

    # Configure logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    asyncio.run(main())
