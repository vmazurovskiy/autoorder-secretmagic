"""Event handlers for messenger events."""

from typing import Any

from src.domain.client import Client
from src.logger.logger import get_logger
from src.logger.types import Category
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
            # В будущем: sales_updated, stock_updated, bom_updated, и т.д.
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
            event_id=event_id,
            event_type=event_type,
            client_id=client_id,
        )

        handler = self._handlers.get(event_type)
        if handler:
            try:
                await handler(event)
                self.logger.info(
                    f"Event processed successfully: {event_type}",
                    event_id=event_id,
                    event_type=event_type,
                    client_id=client_id,
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to process event: {event_type}",
                    e,
                    event_id=event_id,
                    event_type=event_type,
                    client_id=client_id,
                )
                raise
        else:
            self.logger.warn(
                f"Unknown event type: {event_type}",
                event_id=event_id,
                event_type=event_type,
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
                event_id=event.get("event_id"),
            )
            return

        # Создаём Client из event data
        client = Client.from_event_data(data)

        # Логируем features для отладки
        enabled_features = client.get_enabled_features()
        self.logger.debug(
            f"Client features: {enabled_features}",
            client_id=str(client.id),
            client_name=client.name,
            features=enabled_features,
        )

        # Сохраняем/обновляем клиента в БД
        self.client_repository.upsert(client)

        self.logger.info(
            f"Client configuration saved: {client.name}",
            client_id=str(client.id),
            client_name=client.name,
            status=client.status,
            features_count=len(enabled_features),
        )
