"""
Structured logging via structlog.

Dev  → colorized ConsoleRenderer (human-readable)
Prod → JSON lines in GCP Cloud Logging format:
         { "severity": "INFO", "message": "...", "timestamp": "...", ... }

GCP Cloud Logging automatically picks up structured JSON written to stdout
from Cloud Run / GKE. The `severity` field maps to the log entry's severity
level in the Cloud Console (instead of the default `level` key structlog uses).
"""

import logging
import sys
from typing import Any

import structlog


# Map structlog level names → GCP severity values
_GCP_SEVERITY: dict[str, str] = {
    "debug": "DEBUG",
    "info": "INFO",
    "warning": "WARNING",
    "warn": "WARNING",
    "error": "ERROR",
    "critical": "CRITICAL",
}


def _gcp_rename_keys(
    _logger: Any, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Processor: renames structlog keys to match GCP Cloud Logging's JSON schema.
      level  → severity  (GCP uses this for log level filtering)
      event  → message   (GCP uses this as the primary log text)
    Also stamps `service` so every log line is attributable.
    """
    level = event_dict.pop("level", method)
    event_dict["severity"] = _GCP_SEVERITY.get(level.lower(), "DEFAULT")
    event_dict["message"] = event_dict.pop("event", "")
    event_dict.setdefault("service", "routersvc")
    return event_dict


def configure_logging() -> None:
    """
    Call once at app startup (before any loggers are used).
    Reads ENV and LOG_LEVEL from settings.
    """
    from app.config import settings

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        # Merge any context vars bound via structlog.contextvars (e.g. request_id)
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.env == "prod":
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            _gcp_rename_keys,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
