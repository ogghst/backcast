import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


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

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Format
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # Stream Handler (Console)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # File Handler
    file_handler = RotatingFileHandler(
        settings.LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Log initial message
    logger.info(f"Logging initialized. Level: {settings.LOG_LEVEL}")
