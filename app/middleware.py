"""
HTTP middleware.

CloudflareOriginGuard
    Rejects requests that bypass Cloudflare and hit Cloud Run directly.
    Gated on CF_SECRET env var — inactive in dev.

RequestIdMiddleware
    - Assigns a unique request ID (req_<ULID>) to every request.
    - Extracts X-Cloud-Trace-Context injected by Cloud Run and binds
      trace_id + span_id to structlog context so every log line within
      the request carries Cloud Trace linkage automatically.
    - Extracts real client IP from CF-Connecting-IP (Cloudflare) or
      X-Forwarded-For before falling back to the direct remote address.
    - Emits a structured access log line at request completion:
        { "message": "http_request", "method": ..., "path": ...,
          "status": ..., "latency_ms": ..., "client_ip": ... }
      Health-check paths (/healthz, /readyz) are excluded to avoid noise.
"""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from ulid import ULID

logger = structlog.get_logger()

# Paths exempt from the Cloudflare origin guard — Cloud Run health probes
# are called directly by the GCP load balancer, not via Cloudflare.
_CF_EXEMPT_PATHS = {"/healthz", "/readyz"}

# Paths excluded from access logging — high-frequency probes would drown
# out real traffic in Cloud Logging and inflate log ingestion costs.
_ACCESS_LOG_SKIP = {"/healthz", "/readyz"}


def _parse_trace_header(header: str) -> tuple[str | None, str | None, bool]:
    """
    Parse X-Cloud-Trace-Context header.

    Format: ``TRACE_ID/SPAN_ID;o=TRACE_FLAG``
    where TRACE_FLAG is 1 (sampled) or 0 (not sampled).

    Returns (trace_id, span_id, sampled).  Any missing part returns None/False.
    """
    if not header:
        return None, None, False

    trace_id: str | None = None
    span_id:  str | None = None
    sampled = False

    slash_idx = header.find("/")
    if slash_idx == -1:
        # Only trace ID present, no span
        trace_id = header.split(";")[0] or None
    else:
        trace_id = header[:slash_idx] or None
        remainder = header[slash_idx + 1:]
        semi_idx = remainder.find(";")
        if semi_idx == -1:
            span_id = remainder or None
        else:
            span_id = remainder[:semi_idx] or None
            sampled = "o=1" in remainder[semi_idx:]

    return trace_id, span_id, sampled


def _real_client_ip(request: Request) -> str:
    """
    Resolve the original client IP in order of preference:
      1. CF-Connecting-IP  — set by Cloudflare, single real IP
      2. X-Forwarded-For   — leftmost entry (original client)
      3. request.client.host — direct TCP peer (may be a proxy)
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


class CloudflareOriginGuard(BaseHTTPMiddleware):
    """
    Rejects requests that bypass Cloudflare and hit Cloud Run directly.

    Cloudflare is configured to inject `X-CF-Secret: <token>` on every
    proxied request.  Any request arriving without this header (i.e. someone
    hitting the Cloud Run URL directly) is returned a 403 before it reaches
    any route handler.

    Only active when `settings.cf_secret` is non-empty — in dev the check
    is skipped entirely so local testing is unaffected.

    Exempt paths: /healthz and /readyz — these are called by GCP health-check
    probes that cannot inject custom headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        from app.config import settings  # local import avoids circular dependency

        if settings.cf_secret and request.url.path not in _CF_EXEMPT_PATHS:
            incoming = request.headers.get("X-CF-Secret", "")
            if incoming != settings.cf_secret:
                logger.warning(
                    "cf_origin_guard_blocked",
                    path=request.url.path,
                    client_ip=_real_client_ip(request),
                )
                return Response(
                    content='{"error":{"code":"forbidden","message":"Forbidden"}}',
                    status_code=403,
                    media_type="application/json",
                )

        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Per-request observability setup.

    On every inbound request:
      1. Assigns a unique ID (honors X-Request-Id pass-through).
      2. Extracts X-Cloud-Trace-Context for log → Cloud Trace correlation.
      3. Binds request_id, trace_id, span_id to structlog context vars so
         every log call within the request scope carries them automatically.
      4. Emits a structured access log at request completion.
      5. Echoes X-Request-Id in the response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()

        # ── Request ID ────────────────────────────────────────────────────────
        request_id = request.headers.get("X-Request-Id") or f"req_{ULID()}"
        request.state.request_id = request_id

        # ── Cloud Trace context ───────────────────────────────────────────────
        # Cloud Run automatically injects X-Cloud-Trace-Context on every
        # inbound request.  Extracting it here means every log line within
        # this request scope carries the trace/span IDs without any handler
        # needing to pass them manually.
        trace_id, span_id, _sampled = _parse_trace_header(
            request.headers.get("X-Cloud-Trace-Context", "")
        )

        # ── Bind to structlog context ─────────────────────────────────────────
        ctx: dict = {"request_id": request_id}
        if trace_id:
            ctx["trace_id"] = trace_id
        if span_id:
            ctx["span_id"] = span_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**ctx)

        # ── Handle request ────────────────────────────────────────────────────
        response = await call_next(request)
        latency_ms = int((time.monotonic() - start) * 1000)

        # ── Access log ────────────────────────────────────────────────────────
        # Emitted for every request except health probes.  In prod these JSON
        # lines land in Cloud Logging where log-based metrics are derived from
        # them (error rate, latency distribution, request count by path).
        if request.url.path not in _ACCESS_LOG_SKIP:
            client_ip = _real_client_ip(request)
            log_fn = logger.warning if response.status_code >= 400 else logger.info
            log_fn(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                latency_ms=latency_ms,
                client_ip=client_ip,
                user_agent=request.headers.get("user-agent", ""),
                # GCP Cloud Logging recognises the top-level "httpRequest" key
                # and surfaces it as structured HTTP metadata in Logs Explorer.
                httpRequest={
                    "requestMethod": request.method,
                    "requestUrl": request.url.path,
                    "status": response.status_code,
                    "latency": f"{latency_ms / 1000:.3f}s",
                    "userAgent": request.headers.get("user-agent", ""),
                    "remoteIp": client_ip,
                    "protocol": request.scope.get("type", "http").upper(),
                },
            )

        # ── Response header ───────────────────────────────────────────────────
        response.headers["X-Request-Id"] = request_id
        return response
