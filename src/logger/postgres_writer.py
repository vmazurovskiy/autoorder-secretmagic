"""PostgreSQL writer для логов с батчингом."""

import asyncio
import contextlib
import json
import sys
from collections.abc import Sequence
from contextlib import asynccontextmanager
from typing import Any

import psycopg2.extras
from psycopg2.extensions import connection as Connection

from src.logger.types import LogEntry


class PostgresWriter:
    """PostgresWriter записывает логи в PostgreSQL с батчингом."""

    def __init__(
        self,
        dsn: str,
        batch_size: int = 100,
        flush_interval: float = 5.0,
    ) -> None:
        """
        Initialize PostgresWriter.

        Args:
            dsn: PostgreSQL connection string
            batch_size: Размер батча для flush
            flush_interval: Интервал автоматического flush в секундах
        """
        self.dsn = dsn
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer: list[LogEntry] = []
        self._lock = asyncio.Lock()
        self._conn: Connection | None = None
        self._flush_task: asyncio.Task[None] | None = None
        self._closed = False

    async def connect(self) -> None:
        """Подключается к PostgreSQL."""
        try:
            # Используем синхронный psycopg2 (для async можно использовать psycopg)
            self._conn = psycopg2.connect(self.dsn)
            self._conn.set_session(autocommit=False)

            # Запускаем фоновый flush
            self._flush_task = asyncio.create_task(self._background_flush())
        except Exception as e:
            print(
                f"[LOGGER ERROR] Failed to connect to PostgreSQL: {e}",
                file=sys.stderr,
            )
            raise

    async def write(self, entry: LogEntry) -> None:
        """Добавляет запись в буфер."""
        if self._closed:
            return

        async with self._lock:
            self.buffer.append(entry)

            # Автоматический flush при достижении batch_size
            if len(self.buffer) >= self.batch_size:
                await self._flush_locked()

    async def write_batch(self, entries: Sequence[LogEntry]) -> None:
        """Записывает батч записей."""
        if self._closed:
            return

        async with self._lock:
            self.buffer.extend(entries)

            if len(self.buffer) >= self.batch_size:
                await self._flush_locked()

    async def flush(self) -> None:
        """Принудительно записывает буфер в БД."""
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self) -> None:
        """Записывает буфер в БД (должен вызываться с захваченным lock)."""
        if not self.buffer or not self._conn:
            return

        try:
            # Формируем multi-row INSERT
            query = """
                INSERT INTO logs (
                    timestamp, service_name, instance_id, node_name, environment,
                    level, category, trace_id, span_id, request_id,
                    function_name, file_path, line_number,
                    message, error_message, stack_trace, context,
                    duration_ms, ingestion_time
                ) VALUES %s
            """

            values = [
                (
                    entry.timestamp,
                    entry.service_name,
                    entry.instance_id,
                    entry.node_name,
                    entry.environment,
                    entry.level.value,
                    entry.category.value if entry.category else None,
                    entry.trace_id,
                    entry.span_id,
                    entry.request_id,
                    entry.function_name,
                    entry.file_path,
                    entry.line_number,
                    entry.message,
                    entry.error_message,
                    entry.stack_trace,
                    (json.dumps(entry.context) if entry.context is not None else None),
                    entry.duration_ms,
                    entry.ingestion_time,
                )
                for entry in self.buffer
            ]

            # Используем execute_values для bulk insert
            with self._conn.cursor() as cursor:
                psycopg2.extras.execute_values(
                    cursor,
                    query,
                    values,
                    page_size=self.batch_size,
                )
                self._conn.commit()

            # Очищаем буфер после успешной записи
            self.buffer.clear()

        except Exception as e:
            print(
                f"[LOGGER ERROR] Failed to insert logs into PostgreSQL: {e}",
                file=sys.stderr,
            )
            # Rollback транзакции
            if self._conn:
                self._conn.rollback()
            # Fallback в stderr если PostgreSQL недоступен
            self._fallback_to_stderr()

    def _fallback_to_stderr(self) -> None:
        """Записывает логи в stderr если PostgreSQL недоступен."""
        for entry in self.buffer:
            try:
                data: dict[str, Any] = {
                    "timestamp": entry.timestamp.isoformat(),
                    "level": entry.level.value,
                    "category": entry.category.value if entry.category else None,
                    "message": entry.message,
                    "service_name": entry.service_name,
                    "environment": entry.environment,
                }
                if entry.error_message:
                    data["error"] = entry.error_message
                if entry.context:
                    data["context"] = entry.context

                print(json.dumps(data), file=sys.stderr)
            except Exception:
                # Последний fallback - простой текст
                print(
                    f"[{entry.level.value}] {entry.category}: {entry.message}",
                    file=sys.stderr,
                )

    async def _background_flush(self) -> None:
        """Периодически сбрасывает буфер."""
        while not self._closed:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(
                    f"[LOGGER ERROR] Background flush failed: {e}",
                    file=sys.stderr,
                )

    async def close(self) -> None:
        """Закрывает writer и сбрасывает оставшиеся логи."""
        self._closed = True

        # Останавливаем фоновый flush
        if self._flush_task:
            self._flush_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._flush_task

        # Финальный flush
        await self.flush()

        # Закрываем соединение
        if self._conn:
            self._conn.close()
            self._conn = None


@asynccontextmanager
async def create_postgres_writer(
    dsn: str,
    batch_size: int = 100,
    flush_interval: float = 5.0,
) -> Any:
    """
    Context manager для создания PostgresWriter.

    Args:
        dsn: PostgreSQL connection string
        batch_size: Размер батча для flush
        flush_interval: Интервал автоматического flush в секундах

    Yields:
        PostgresWriter instance
    """
    writer = PostgresWriter(dsn, batch_size, flush_interval)
    await writer.connect()
    try:
        yield writer
    finally:
        await writer.close()
