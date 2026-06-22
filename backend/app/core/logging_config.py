from __future__ import annotations

import json
import logging
import time
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object.

    Extra fields passed via ``logger.info("msg", extra={...})`` are merged
    into the top-level JSON object, making structured queries easy in any
    log aggregator.
    """

    _RESERVED = frozenset(logging.LogRecord(
        "", 0, "", 0, "", (), None
    ).__dict__.keys()) | {"message", "asctime"}

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        payload: dict[str, Any] = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
        }

        # Merge caller-supplied extra fields (request_id, method, path, …).
        for key, value in record.__dict__.items():
            if key not in self._RESERVED:
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger with JSON output.

    Call once at application startup, before the FastAPI app is created.
    Subsequent ``logging.getLogger(__name__)`` calls in any module will
    inherit this configuration automatically.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    # Quieten noisy libraries that aren't useful at INFO level.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
