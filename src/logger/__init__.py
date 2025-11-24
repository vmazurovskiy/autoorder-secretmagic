"""Logger module for SecretMagic microservice."""

from src.logger.logger import Logger, get_logger
from src.logger.postgres_writer import PostgresWriter
from src.logger.types import Category, Field, Level, LogEntry

__all__ = [
    "Logger",
    "get_logger",
    "PostgresWriter",
    "Category",
    "Level",
    "LogEntry",
    "Field",
]
