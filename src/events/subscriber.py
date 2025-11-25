"""Event subscriber for Redis Streams."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from src.events.client import RedisClient
from src.logger.logger import get_logger
from src.logger.types import Category


class EventSubscriber:
    """
    Event subscriber для чтения из Redis Streams с использованием consumer groups.

    Использует XREADGROUP для надёжного распределённого чтения:
    - Автоматически создаёт consumer group если нужно
    - Читает только новые сообщения (>)
    - ACK сообщения после успешной обработки
    - Graceful shutdown с завершением текущей обработки
    """

    def __init__(
        self,
        redis_client: RedisClient,
        consumer_group: str,
        streams: list[str],
    ) -> None:
        """
        Initialize EventSubscriber.

        Args:
            redis_client: Redis client instance
            consumer_group: Consumer group name (e.g., "secretmagic-dev")
            streams: List of stream names to subscribe (e.g., ["clients-updates"])
        """
        self.redis_client = redis_client
        self.consumer_group = consumer_group
        self.streams = streams
        self.consumer_name = f"{consumer_group}-consumer-{id(self)}"
        self._stopped = False
        self.logger = get_logger().with_category(Category.MESSENGER)

    async def consume(self, handler: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        """
        Start consuming events from Redis Streams.

        Args:
            handler: Async function to handle each event
        """
        redis = self.redis_client.get_redis()

        # Создаём consumer groups для всех streams (если не существуют)
        for stream in self.streams:
            try:
                await redis.xgroup_create(
                    name=stream,
                    groupname=self.consumer_group,
                    id="0",  # Начинаем с начала stream (для новых групп)
                    mkstream=True,  # Создать stream если не существует
                )
                self.logger.info(
                    f"Created consumer group '{self.consumer_group}' for stream '{stream}'"
                )
            except Exception as e:
                # BUSYGROUP - группа уже существует, это ОК
                if "BUSYGROUP" not in str(e):
                    self.logger.warn(
                        f"Failed to create consumer group for stream '{stream}': {e}"
                    )

        self.logger.info(
            f"Starting event consumer: group={self.consumer_group}, streams={self.streams}"
        )

        # Главный цикл чтения событий
        while not self._stopped:
            try:
                # XREADGROUP: читаем новые сообщения ('>') с блокировкой
                # Формат: {stream1: '>', stream2: '>'}
                streams_dict = {stream: ">" for stream in self.streams}

                messages = await redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams=streams_dict,
                    count=10,  # Батч до 10 сообщений
                    block=5000,  # Блокировка на 5 сек (для graceful shutdown)
                )

                # Обрабатываем полученные сообщения
                for stream, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        await self._handle_message(
                            stream, message_id, message_data, handler
                        )

            except asyncio.CancelledError:
                self.logger.info("Consumer cancelled, stopping...")
                break
            except Exception as e:
                self.logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(5)  # Backoff before retry

        self.logger.info("Event consumer stopped")

    async def _handle_message(
        self,
        stream: str,
        message_id: str,
        message_data: dict[str, Any],
        handler: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """
        Handle single message from stream.

        Args:
            stream: Stream name
            message_id: Message ID in Redis Stream
            message_data: Message data dict
            handler: Handler function
        """
        try:
            # Парсим event (data хранится как JSON string)
            event = self._parse_event(message_data)

            # Логируем получение события
            self.logger.debug(
                f"Received event from stream '{stream}'",
                event_id=event.get("event_id"),
                event_type=event.get("event_type"),
                client_id=event.get("client_id"),
            )

            # Обрабатываем событие через handler
            await handler(event)

            # ACK сообщение после успешной обработки
            redis = self.redis_client.get_redis()
            await redis.xack(stream, self.consumer_group, message_id)

            self.logger.debug(
                f"Event processed and ACKed",
                event_id=event.get("event_id"),
                message_id=message_id,
            )

        except Exception as e:
            self.logger.error(
                f"Failed to handle message from stream '{stream}'",
                e,
                message_id=message_id,
                message_data=message_data,
            )
            # НЕ ACK при ошибке - сообщение останется в pending list
            # Можно реализовать retry logic через XPENDING

    def _parse_event(self, message_data: dict[str, Any]) -> dict[str, Any]:
        """
        Parse event from Redis Stream message.

        Args:
            message_data: Raw message data from Redis

        Returns:
            Parsed event dict
        """
        event = {
            "event_id": message_data.get("event_id"),
            "event_type": message_data.get("event_type"),
            "client_id": message_data.get("client_id"),
            "timestamp": message_data.get("timestamp"),
        }

        # Парсим data из JSON string
        data_json = message_data.get("data", "{}")
        try:
            event["data"] = json.loads(data_json)
        except json.JSONDecodeError:
            event["data"] = {}

        return event

    async def stop(self) -> None:
        """Stop consuming events gracefully."""
        self.logger.info("Stopping event consumer...")
        self._stopped = True
