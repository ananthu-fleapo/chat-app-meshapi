"""
Structured logging via structlog.

Dev  → colorized ConsoleRenderer (human-readable)
Prod → JSON lines in GCP Cloud Logging format:
         { "severity": "INFO", "message": "...", "timestamp": "...", ... }

GCP Cloud Logging automatically picks up structured JSON written to stdout
from Cloud Run / GKE.

Special GCP fields emitted in prod:
  severity                           → log entry severity level
  message                            → primary log text
  logging.googleapis.com/trace       → links log to Cloud Trace span
  logging.googleapis.com/spanId      → span within the trace
  logging.googleapis.com/labels      → indexed labels for filtering
  httpRequest                        → parsed by Cloud Logging as HTTP metadata
"""

import logging
import sys
from typing import Any

import structlog

_HEALTH_PATHS = ("/healthz", "/readyz", "/favicon.ico", "/metrics")


class _HealthCheckFilter(logging.Filter):
    """Drop uvicorn access log records for health-probe paths."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not any(path in record.getMessage() for path in _HEALTH_PATHS)


# Map structlog level names → GCP severity values.
_GCP_SEVERITY: dict[str, str] = {
    "debug":    "DEBUG",
    "info":     "INFO",
    "warning":  "WARNING",
    "warn":     "WARNING",
    "error":    "ERROR",
    "critical": "CRITICAL",
}


def _make_gcp_processor(project_id: str):
    """
    Returns a structlog processor that rewrites keys for GCP Cloud Logging.

    Captures ``project_id`` at configure-time (no per-call import needed).

    Transformations:
      level  → severity   (GCP uses this for log-level filtering & colouring)
      event  → message    (GCP uses this as the primary log text)
      trace_id → logging.googleapis.com/trace  (links to Cloud Trace)
      span_id  → logging.googleapis.com/spanId

    Also stamps static labels so every log line is filterable by service.
    """
    def _processor(_logger: Any, method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        # ── level / severity ─────────────────────────────────────────────────
        level = event_dict.pop("level", method)
        event_dict["severity"] = _GCP_SEVERITY.get(level.lower(), "DEFAULT")

        # ── event / message ──────────────────────────────────────────────────
        event_dict["message"] = event_dict.pop("event", "")

        # ── Cloud Trace linkage ───────────────────────────────────────────────
        # trace_id and span_id are bound to structlog context by
        # RequestIdMiddleware from the X-Cloud-Trace-Context header injected
        # by Cloud Run.  If present they enable log → trace correlation in
        # the Cloud Console (Logs Explorer → "Open in Trace").
        trace_id = event_dict.pop("trace_id", None)
        span_id  = event_dict.pop("span_id", None)

        if trace_id and project_id:
            event_dict["logging.googleapis.com/trace"] = (
                f"projects/{project_id}/traces/{trace_id}"
            )
        if span_id:
            event_dict["logging.googleapis.com/spanId"] = span_id

        # ── Indexed labels ────────────────────────────────────────────────────
        # Appear as searchable labels in Cloud Logging. Useful for dashboards
        # that filter by service without parsing jsonPayload.
        event_dict["logging.googleapis.com/labels"] = {"service": "routersvc"}

        # ── Service stamp ─────────────────────────────────────────────────────
        event_dict.setdefault("service", "routersvc")

        return event_dict

    return _processor


def configure_logging() -> None:
    """
    Call once at app startup (before any loggers are used).
    Reads ENV, LOG_LEVEL, and GCP_PROJECT_ID from settings.
    """
    from app.config import settings

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        # Merge context vars bound via structlog.contextvars
        # (e.g. request_id, trace_id, span_id bound by RequestIdMiddleware).
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.env == "prod":
        processors: list[Any] = shared_processors + [
            structlog.processors.format_exc_info,
            _make_gcp_processor(settings.gcp_project_id),
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

    # Suppress uvicorn's built-in access log for health-probe paths.
    logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())
