import json
import logging
import sys
from typing import Any

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """Single-line JSON logs so a log aggregator (Railway logs, Datadog,
    etc.) can parse fields instead of grepping free text."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key.startswith("ctx_"):
                payload[key[4:]] = value
        return json.dumps(payload)


def configure_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if settings.ENVIRONMENT == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))

    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Quiet noisy libraries down to warnings; app code stays at INFO.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.ENVIRONMENT == "development" else logging.WARNING
    )


def log_request(logger: logging.Logger, method: str, path: str, status_code: int, duration_ms: float) -> None:
    logger.info(
        f"{method} {path} {status_code} {duration_ms:.1f}ms",
        extra={
            "ctx_http_method": method,
            "ctx_http_path": path,
            "ctx_http_status": status_code,
            "ctx_duration_ms": round(duration_ms, 1),
        },
    )
