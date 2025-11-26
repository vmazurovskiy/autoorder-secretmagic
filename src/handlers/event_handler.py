"""Event handlers for messenger events."""

from typing import Any

from src.domain.client import Client
from src.logger.logger import get_logger
from src.logger.types import Category, param
from src.repository.client_repository import ClientRepository


class EventHandler:
    """
    Handler for processing events from messenger (Redis Streams).

    Routes events by type to appropriate handlers.
    """

    def __init__(self, client_repository: ClientRepository) -> None:
        """
        Initialize EventHandler.

        Args:
            client_repository: Repository for client operations
        """
        self.client_repository = client_repository
        self.logger = get_logger().with_category(Category.MESSENGER)

        # Маппинг event_type -> handler method
        self._handlers: dict[str, Any] = {
            "clients_updated": self._handle_clients_updated,
            "sales_updated": self._handle_sales_updated,
            # В будущем: stock_updated, bom_updated, и т.д.
        }

    async def handle(self, event: dict[str, Any]) -> None:
        """
        Handle incoming event.

        Routes event to appropriate handler based on event_type.

        Args:
            event: Event dict with event_type, client_id, data, etc.
        """
        event_type = event.get("event_type")
        event_id = event.get("event_id")
        client_id = event.get("client_id")

        self.logger.info(
            f"Processing event: {event_type}",
            param("event_id", event_id),
            param("event_type", event_type),
            param("client_id", client_id),
        )

        handler = self._handlers.get(event_type or "")
        if handler:
            try:
                await handler(event)
                self.logger.info(
                    f"Event processed successfully: {event_type}",
                    param("event_id", event_id),
                    param("event_type", event_type),
                    param("client_id", client_id),
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to process event: {event_type}",
                    e,
                    param("event_id", event_id),
                    param("event_type", event_type),
                    param("client_id", client_id),
                )
                raise
        else:
            self.logger.warn(
                f"Unknown event type: {event_type}",
                param("event_id", event_id),
                param("event_type", event_type),
            )

    async def _handle_clients_updated(self, event: dict[str, Any]) -> None:
        """
        Handle clients_updated event.

        Creates or updates client configuration in PostgreSQL.
        Uses Event Carried State Transfer pattern - event contains full client state.

        Args:
            event: Event with client data in 'data' field
        """
        data = event.get("data", {})
        if not data:
            self.logger.warn(
                "clients_updated event has empty data",
                param("event_id", event.get("event_id")),
            )
            return

        # Создаём Client из event data
        client = Client.from_event_data(data)

        # Логируем features для отладки
        enabled_features = client.get_enabled_features()
        self.logger.debug(
            f"Client features: {enabled_features}",
            param("client_id", str(client.id)),
            param("client_name", client.name),
            param("features", enabled_features),
        )

        # Сохраняем/обновляем клиента в БД
        self.client_repository.upsert(client)

        self.logger.info(
            f"Client configuration saved: {client.name}",
            param("client_id", str(client.id)),
            param("client_name", client.name),
            param("status", client.status),
            param("features_count", len(enabled_features)),
        )

    async def _handle_sales_updated(self, event: dict[str, Any]) -> None:
        """
        Handle sales_updated event.

        Event Notification Pattern - событие содержит только метаданные.
        Полные данные нужно читать из StarRocks по client_id.

        Формат data:
            - table_name: название таблицы (например, "c2_sales")
            - record_count: количество обновлённых записей
            - updated_at: время обновления данных

        Args:
            event: Event with sales metadata in 'data' field
        """
        event_id = event.get("event_id")
        client_id = event.get("client_id")
        timestamp = event.get("timestamp")
        data = event.get("data", {})

        if not client_id:
            self.logger.warn(
                "sales_updated event has no client_id",
                param("event_id", event_id),
            )
            return

        # Извлекаем метаданные из события
        table_name = data.get("table_name", "unknown")
        record_count = data.get("record_count", 0)
        updated_at = data.get("updated_at", timestamp)

        # Проверяем, есть ли клиент в нашей БД
        client = self.client_repository.get_by_id(client_id)
        client_name = client.name if client else "unknown"
        client_status = client.status if client else "not_found"

        self.logger.info(
            f"Sales data updated for client: {client_name}",
            param("event_id", event_id),
            param("client_id", client_id),
            param("client_name", client_name),
            param("client_status", client_status),
            param("table_name", table_name),
            param("record_count", record_count),
            param("updated_at", updated_at),
        )

        # TODO: Далее здесь будет логика:
        # 1. Проверить, что клиент active и config_confirmed
        # 2. Определить, какие данные новые (сравнить с last_processed_at)
        # 3. Запустить feature engineering для нового периода
        # 4. Обновить last_processed_at для клиента
