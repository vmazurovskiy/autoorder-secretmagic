"""Client domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class Client:
    """
    Client configuration model.

    Represents a client with their enabled features and configuration.
    Synchronized from integrator via messenger (Redis Streams).
    """

    id: UUID
    name: str
    organization_id: str
    status: str = "active"
    contact_email: str | None = None
    contact_phone: str | None = None
    features_enabled: dict[str, bool] = field(default_factory=dict)
    config_confirmed: bool = False
    config_confirmed_by: str | None = None
    config_confirmed_at: datetime | None = None
    source: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    synced_at: datetime = field(default_factory=datetime.utcnow)

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled for this client."""
        return self.features_enabled.get(feature, False)

    def get_enabled_features(self) -> list[str]:
        """Get list of enabled feature names."""
        return [f for f, enabled in self.features_enabled.items() if enabled]

    @classmethod
    def from_event_data(cls, data: dict[str, Any]) -> "Client":
        """
        Create Client from messenger event data.

        Args:
            data: Event data dict from clients_updated event

        Returns:
            Client instance
        """
        from uuid import UUID as UUIDType

        # Parse timestamps
        created_at = cls._parse_timestamp(data.get("created_at"))
        updated_at = cls._parse_timestamp(data.get("updated_at"))
        config_confirmed_at = cls._parse_timestamp(data.get("config_confirmed_at"))

        return cls(
            id=UUIDType(data["id"]),
            name=data.get("name", ""),
            organization_id=data.get("organization_id", ""),
            contact_email=data.get("contact_email"),
            contact_phone=data.get("contact_phone"),
            status=data.get("status", "active"),
            features_enabled=data.get("features_enabled", {}),
            config_confirmed=data.get("config_confirmed", False),
            config_confirmed_by=data.get("config_confirmed_by"),
            config_confirmed_at=config_confirmed_at,
            source=data.get("source"),
            created_at=created_at or datetime.utcnow(),
            updated_at=updated_at or datetime.utcnow(),
            synced_at=datetime.utcnow(),
        )

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        """Parse ISO timestamp string to datetime."""
        if not value:
            return None
        try:
            # Handle RFC3339 format with timezone
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
