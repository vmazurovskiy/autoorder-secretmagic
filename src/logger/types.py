"""Types and constants for structured logging."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Level(str, Enum):
    """Log level определяет уровень важности лога."""

    TRACE = "trace"  # Детальная трассировка выполнения
    DEBUG = "debug"  # Отладочная информация
    INFO = "info"  # Информационные сообщения
    WARN = "warn"  # Предупреждения
    ERROR = "error"  # Ошибки (recoverable)
    FATAL = "fatal"  # Критические ошибки (требуют вмешательства)
    PANIC = "panic"  # Паника (программа падает)


class Category(str, Enum):
    """Category определяет категорию события для группировки логов."""

    FEATURE_ENGINEERING = "feature_engineering"  # Feature Engineering процессы
    BOM_EXPLOSION = "bom_explosion"  # BOM Explosion
    DATABASE = "database"  # Операции с БД
    MESSENGER = "messenger"  # Event messaging (Redis Streams)
    PIPELINE = "pipeline"  # Data pipeline
    STARROCKS = "starrocks"  # StarRocks queries
    CACHE = "cache"  # Кеширование
    SECURITY = "security"  # События безопасности
    EXTERNAL_API = "external_api"  # Внешние API (Yandex, Open-Meteo)


@dataclass
class LogEntry:
    """LogEntry представляет одну запись лога для вставки в PostgreSQL."""

    timestamp: datetime
    service_name: str
    instance_id: str
    environment: str
    level: Level
    message: str
    ingestion_time: datetime = field(default_factory=datetime.utcnow)
    node_name: str | None = None
    category: Category | None = None
    trace_id: str | None = None
    span_id: str | None = None
    request_id: str | None = None
    function_name: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    error_message: str | None = None
    stack_trace: str | None = None
    context: dict[str, Any] | None = None
    duration_ms: int | None = None


@dataclass
class Field:
    """Field для структурированных данных в логах."""

    key: str
    value: Any


# Helper функции для создания полей


def category(cat: Category) -> Field:
    """Создаёт поле для категории лога."""
    return Field(key="_category", value=cat)


def param(key: str, value: Any) -> Field:
    """Универсальная функция для добавления параметра."""
    return Field(key=key, value=value)


def string(key: str, value: str) -> Field:
    """Создаёт строковое поле."""
    return Field(key=key, value=value)


def integer(key: str, value: int) -> Field:
    """Создаёт целочисленное поле."""
    return Field(key=key, value=value)


def boolean(key: str, value: bool) -> Field:
    """Создаёт булево поле."""
    return Field(key=key, value=value)


def duration_ms(value: int) -> Field:
    """Создаёт поле для duration в миллисекундах."""
    return Field(key="duration_ms", value=value)


def error(err: Exception) -> Field:
    """Создаёт поле для ошибки."""
    return Field(key="error", value=str(err))
