import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


class LocalTimeFormatter(logging.Formatter):
    """Render ``%(asctime)s`` in the process-local timezone with a numeric UTC
    offset (e.g. ``+02:00``), keeping millisecond precision.

    The host clock, app.log lines, and Postgres all display Europe/Rome in this
    deployment, so timestamps line up across ``date`` / logs / DB rows.
    ``timestamptz`` storage stays absolute UTC regardless — this only affects
    the log display format.
    """

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        base = super().formatTime(record, datefmt)
        if datefmt:
            # Caller controls the full format; don't append an offset.
            return base
        offset = time.strftime("%z", self.converter(record.created))  # e.g. +0200
        if len(offset) >= 5:
            offset = f"{offset[:3]}:{offset[3:]}"  # -> +02:00
        return f"{base}{offset}"


def setup_logging() -> None:
    """
    Configure logging for the application.
    Sets up a logger with both stream (console) and file handlers.
    """
    # Create logs directory if it doesn't exist
    log_file_path = Path(settings.LOG_FILE)
    log_dir = log_file_path.parent
    if not log_dir.exists():
        os.makedirs(log_dir, exist_ok=True)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LEVEL)

    # Silence chatty HTTP-client libraries. httpx/httpcore emit an INFO line
    # per request (e.g. every Telegram sendMessage / getUpdates), which floods
    # app.log with Telegram API call noise. Warnings/errors still surface.
    for _noisy in ("httpx", "httpcore"):
        logging.getLogger(_noisy).setLevel(logging.WARNING)

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Format — local time with a numeric UTC offset (see LocalTimeFormatter).
    # App logs, the host clock, and Postgres all display Europe/Rome, so UI
    # actions <-> logs <-> DB rows line up without the local-vs-UTC offset
    # friction. timestamptz storage stays absolute UTC.
    formatter = LocalTimeFormatter(settings.LOG_FORMAT)
    formatter.converter = time.localtime  # process-local = Europe/Rome on host

    # Stream Handler (Console)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # File Handler with rotating logs
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Log initial message
    logger.info(f"Logging initialized. Level: {settings.LOG_LEVEL}")
