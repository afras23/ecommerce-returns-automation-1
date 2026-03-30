"""
Structured JSON logging setup and helpers.

Configures the root logger with a JSON formatter for production-style logs.
"""

import logging
import sys
from datetime import UTC, datetime


class StructuredFormatter(logging.Formatter):
    """Emit each log record as a single JSON object per line."""

    _SKIP = frozenset(
        {
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "name",
            "message",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in self._SKIP:
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def setup_logging() -> None:
    """Configure root logging with structured JSON output."""
    from app.config import settings

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Ensure uvicorn loggers propagate to root
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger (uses root configuration after setup_logging)."""
    return logging.getLogger(name)
