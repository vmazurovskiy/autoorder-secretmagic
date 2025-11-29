"""Configuration domain models."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConfigEntry:
    """Single configuration entry."""

    key: str
    value: str
    description: str | None = None
    updated_at: datetime | None = None
    updated_by: str = "system"
