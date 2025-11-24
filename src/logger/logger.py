"""Основной logger для структурированного логирования."""

import inspect
import os
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from src.logger.postgres_writer import PostgresWriter
from src.logger.types import Category, Field, Level, LogEntry


class Logger:
    """Logger для структурированного логирования с записью в PostgreSQL."""

    def __init__(
        self,
        service_name: str,
        environment: str,
        writer: PostgresWriter | None = None,
    ) -> None:
        """
        Initialize Logger.

        Args:
            service_name: Имя сервиса
            environment: Окружение (dev, stage, prod)
            writer: PostgresWriter для записи логов
        """
        self.service_name = service_name
        self.environment = environment
        self.writer = writer
        self.instance_id = self._get_instance_id()
        self.node_name = self._get_node_name()

        # Контекстные поля
        self._fields: dict[str, Any] = {}
        self._category: Category | None = None
        self._trace_id: str | None = None
        self._span_id: str | None = None
        self._request_id: str | None = None

    def trace(self, msg: str, *fields: Field) -> None:
        """Log trace level message."""
        self._log(Level.TRACE, msg, None, *fields)

    def debug(self, msg: str, *fields: Field) -> None:
        """Log debug level message."""
        self._log(Level.DEBUG, msg, None, *fields)

    def info(self, msg: str, *fields: Field) -> None:
        """Log info level message."""
        self._log(Level.INFO, msg, None, *fields)

    def warn(self, msg: str, *fields: Field) -> None:
        """Log warn level message."""
        self._log(Level.WARN, msg, None, *fields)

    def error(self, msg: str, err: Exception | None = None, *fields: Field) -> None:
        """Log error level message."""
        self._log(Level.ERROR, msg, err, *fields)

    def fatal(self, msg: str, err: Exception | None = None, *fields: Field) -> None:
        """Log fatal level message and exit."""
        self._log(Level.FATAL, msg, err, *fields)
        raise SystemExit(1)

    def panic(self, msg: str, err: Exception | None = None, *fields: Field) -> None:
        """Log panic level message and raise."""
        self._log(Level.PANIC, msg, err, *fields)
        raise RuntimeError(msg)

    def _log(
        self,
        level: Level,
        msg: str,
        err: Exception | None,
        *fields: Field,
    ) -> None:
        """Основной метод логирования."""
        # Получаем информацию о caller
        frame = inspect.currentframe()
        caller_frame = (
            frame.f_back.f_back if frame and frame.f_back else None
        )

        function_name = None
        file_path = None
        line_number = None

        if caller_frame:
            function_name = caller_frame.f_code.co_name
            file_path = self._clean_file_path(caller_frame.f_code.co_filename)
            line_number = caller_frame.f_lineno

        # Формируем context из полей
        context: dict[str, Any] = dict(self._fields)
        category = self._category

        for field in fields:
            # Извлекаем категорию если она задана
            if field.key == "_category":
                if isinstance(field.value, Category):
                    category = field.value
                continue
            context[field.key] = field.value

        # Извлекаем duration_ms если есть
        duration_ms = context.pop("duration_ms", None)
        if duration_ms is not None:
            duration_ms = int(duration_ms)

        # Создаём запись лога
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            service_name=self.service_name,
            instance_id=self.instance_id,
            node_name=self.node_name,
            environment=self.environment,
            level=level,
            category=category,
            trace_id=self._trace_id,
            span_id=self._span_id,
            request_id=self._request_id,
            function_name=function_name,
            file_path=file_path,
            line_number=line_number,
            message=msg,
            context=context if context else None,
            duration_ms=duration_ms,
        )

        # Добавляем информацию об ошибке
        if err:
            entry.error_message = str(err)
            # Stack trace только для серьёзных ошибок
            if level in (Level.ERROR, Level.FATAL, Level.PANIC):
                entry.stack_trace = "".join(
                    traceback.format_exception(type(err), err, err.__traceback__)
                )

        # Записываем лог через writer
        if self.writer:
            try:
                # Используем asyncio.create_task для async write
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.writer.write(entry))
                except RuntimeError:
                    # Нет running loop - синхронная запись в буфер
                    asyncio.run(self.writer.write(entry))
            except Exception as write_err:
                print(f"[LOGGER ERROR] Failed to write log: {write_err}")
        else:
            # Fallback: пишем в stdout если writer не инициализирован
            print(f"[{entry.level.value}] {entry.category}: {entry.message}")

    def with_category(self, category: Category) -> "Logger":
        """Возвращает новый logger с указанной категорией."""
        new_logger = Logger(self.service_name, self.environment, self.writer)
        new_logger.instance_id = self.instance_id
        new_logger.node_name = self.node_name
        new_logger._fields = dict(self._fields)
        new_logger._category = category
        new_logger._trace_id = self._trace_id
        new_logger._span_id = self._span_id
        new_logger._request_id = self._request_id
        return new_logger

    def with_trace_id(self, trace_id: str) -> "Logger":
        """Возвращает новый logger с trace ID."""
        new_logger = (
            self.with_category(self._category)
            if self._category
            else self._copy()
        )
        new_logger._trace_id = trace_id
        return new_logger

    def with_span_id(self, span_id: str) -> "Logger":
        """Возвращает новый logger с span ID."""
        new_logger = self._copy()
        new_logger._span_id = span_id
        return new_logger

    def with_request_id(self, request_id: str) -> "Logger":
        """Возвращает новый logger с request ID."""
        new_logger = self._copy()
        new_logger._request_id = request_id
        return new_logger

    def with_fields(self, *fields: Field) -> "Logger":
        """Возвращает новый logger с дополнительными полями."""
        new_logger = self._copy()
        for field in fields:
            new_logger._fields[field.key] = field.value
        return new_logger

    def _copy(self) -> "Logger":
        """Создаёт копию logger."""
        new_logger = Logger(self.service_name, self.environment, self.writer)
        new_logger.instance_id = self.instance_id
        new_logger.node_name = self.node_name
        new_logger._fields = dict(self._fields)
        new_logger._category = self._category
        new_logger._trace_id = self._trace_id
        new_logger._span_id = self._span_id
        new_logger._request_id = self._request_id
        return new_logger

    @staticmethod
    def _get_instance_id() -> str:
        """Получает уникальный ID инстанса из env или генерирует."""
        # Kubernetes pod name
        if hostname := os.getenv("HOSTNAME"):
            return hostname
        # Docker container ID
        if container_id := os.getenv("CONTAINER_ID"):
            return container_id
        # Генерируем UUID для локальной разработки
        return str(uuid.uuid4())

    @staticmethod
    def _get_node_name() -> str | None:
        """Получает имя ноды из env (для K8s/Swarm)."""
        return os.getenv("NODE_NAME")

    @staticmethod
    def _clean_file_path(file_path: str) -> str:
        """Очищает путь к файлу от абсолютного пути."""
        path = Path(file_path)

        # Ищем /src/ в пути
        parts = path.parts
        if "src" in parts:
            idx = parts.index("src")
            return str(Path(*parts[idx:]))

        # Если не нашли - возвращаем только имя файла
        return path.name


# Глобальный logger instance
_global_logger: Logger | None = None


def get_logger() -> Logger:
    """Возвращает глобальный logger instance."""
    global _global_logger
    if _global_logger is None:
        raise RuntimeError("Logger not initialized. Call init_logger() first.")
    return _global_logger


def init_logger(
    service_name: str,
    environment: str,
    writer: PostgresWriter | None = None,
) -> Logger:
    """
    Инициализирует глобальный logger.

    Args:
        service_name: Имя сервиса
        environment: Окружение (dev, stage, prod)
        writer: PostgresWriter для записи логов

    Returns:
        Logger instance
    """
    global _global_logger
    _global_logger = Logger(service_name, environment, writer)
    return _global_logger
