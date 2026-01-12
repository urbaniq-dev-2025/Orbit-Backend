import logging
import sys
from typing import Any

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s | "
    "module=%(module)s function=%(funcName)s line=%(lineno)d"
)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structured logging for the application."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, message: str, **extra: Any) -> None:
    """Log an exception with structured context."""
    logger.exception(message, extra=extra)

