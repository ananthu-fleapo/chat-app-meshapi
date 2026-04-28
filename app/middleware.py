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

RequestLoggingMiddleware
    Raw ASGI middleware that persists every HTTP request + response to MongoDB.
    - Uses raw ASGI (not BaseHTTPMiddleware) so SSE streaming is not buffered.
    - Wraps receive() to capture the request body without blocking downstream.
    - Wraps send() to accumulate response chunks; fires the MongoDB write after
      the final chunk (more_body=False) as an asyncio background task.
    - Strips Authorization, X-Origin-Secret, and Cookie headers before storage.
    - Skips /healthz, /readyz, /metrics — high-frequency probes add noise.
    - Gracefully no-ops when MongoDB is not configured (mongodb_url = "").
"""

import asyncio
import json
import time
from datetime import UTC, datetime

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from ulid import ULID

logger = structlog.get_logger()

# Paths exempt from the Cloudflare origin guard — Cloud Run health probes
# are called directly by the GCP load balancer, not via Cloudflare.
_CF_EXEMPT_PATHS = {"/healthz", "/readyz"}

# Paths excluded from access logging — high-frequency probes would drown
# out real traffic in Cloud Logging and inflate log ingestion costs.
_ACCESS_LOG_SKIP = {"/healthz", "/readyz", "/metrics"}

# Paths excluded from MongoDB request logging
_REQUEST_LOG_SKIP = {"/healthz", "/readyz", "/metrics"}

# Headers stripped before persisting to MongoDB — never store credentials
_SENSITIVE_HEADERS = {"authorization", "x-origin-secret", "cookie", "x-api-key"}

# Paths excluded from MongoDB request logging
_REQUEST_LOG_SKIP = {"/healthz", "/readyz", "/metrics"}

# Headers stripped before persisting to MongoDB — never store credentials
_SENSITIVE_HEADERS = {"authorization", "x-origin-secret", "cookie", "x-api-key"}


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


def _client_ip_from_scope(scope: Scope, headers: dict[str, str]) -> str:
    """Resolve real client IP from raw ASGI scope (no Request object)."""
    cf_ip = headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    xff = headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


class CloudflareOriginGuard(BaseHTTPMiddleware):
    """
    Rejects requests that bypass Cloudflare and hit Cloud Run directly.

    Cloudflare is configured to inject `X-Origin-Secret: <token>` on every
    proxied request via a Request Header Transform rule.  Any request arriving
    without this header (i.e. someone hitting the Cloud Run URL directly) is
    returned a 403 before it reaches any route handler.

    Note: X-CF-* headers are reserved by Cloudflare and cannot be set via
    transform rules — hence X-Origin-Secret is used instead.

    Only active when `settings.cf_secret` is non-empty — in dev the check
    is skipped entirely so local testing is unaffected.

    Exempt paths: /healthz and /readyz — these are called by GCP health-check
    probes that cannot inject custom headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        from app.config import settings  # local import avoids circular dependency

        if settings.cf_secret and request.url.path not in _CF_EXEMPT_PATHS:
            incoming = request.headers.get("X-Origin-Secret", "")
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
        # Also store directly on the scope dict so raw ASGI middleware
        # (RequestLoggingMiddleware) can read it without going through
        # scope["state"], which BaseHTTPMiddleware may not propagate reliably.
        request.scope["_request_id"] = request_id

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
                owner=request.scope.get("_owner"),
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


class RequestLoggingMiddleware:
    """
    Raw ASGI middleware — persists every request + response to MongoDB.

    Why raw ASGI instead of BaseHTTPMiddleware:
    BaseHTTPMiddleware buffers the entire streaming response before returning it,
    which breaks SSE (the client never receives chunks until the stream ends).
    Raw ASGI lets us wrap send() to tap each chunk as it flows through without
    delaying delivery.

    Flow:
      receive_wrapper  — accumulates request body chunks as they arrive
      send_wrapper     — forwards each response chunk immediately to the client
                         AND appends it to a local buffer; when more_body=False
                         the full request+response is written to MongoDB async
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Only instrument HTTP; pass websocket/lifespan through untouched
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from app.config import settings
        from app.db.mongo import is_mongo_available

        path = scope.get("path", "")
        mongo_ok = is_mongo_available()

        # Skip noisy health/metrics endpoints
        if path in _REQUEST_LOG_SKIP:
            await self.app(scope, receive, send)
            return

        # ── Wrap receive to capture request body ──────────────────────────────
        # Body capture runs regardless of mongo availability so the outer
        # RequestIdMiddleware can include it in the http_request access log.
        body_chunks: list[bytes] = []

        async def receive_wrapper() -> Message:
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                if chunk:
                    body_chunks.append(chunk)
                if not message.get("more_body", False):
                    scope["_request_body"] = b"".join(body_chunks)
            return message

        if not mongo_ok:
            logger.warning("request_log_skipped_no_mongo", path=path)
            await self.app(scope, receive_wrapper, send)
            return

        # ── Capture request_id early ──────────────────────────────────────────
        # Read from scope["_request_id"] set directly by RequestIdMiddleware,
        # NOT from scope["state"] which BaseHTTPMiddleware doesn't propagate
        # reliably to inner raw ASGI middleware.
        request_id: str = scope.get("_request_id") or f"req_{ULID()}"

        # ── Decode request headers once ───────────────────────────────────────
        raw_headers: dict[str, str] = {
            k.decode("latin-1"): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }
        safe_headers: dict[str, str] = {
            k: v for k, v in raw_headers.items()
            if k.lower() not in _SENSITIVE_HEADERS
        }

        # ── Wrap send to capture response ─────────────────────────────────────
        response_chunks: list[bytes] = []
        status_code: int = 0
        response_headers: dict[str, str] = {}
        start_time = time.monotonic()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_headers

            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                response_headers = {
                    k.decode("latin-1"): v.decode("latin-1")
                    for k, v in message.get("headers", [])
                }

            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                if chunk:
                    response_chunks.append(chunk)

                if not message.get("more_body", False):
                    # Last byte sent — schedule MongoDB write in background
                    latency_ms = int((time.monotonic() - start_time) * 1000)
                    # request_id captured at __call__ entry (see above).
                    # owner is set by the auth dep via scope["_owner"] (not
                    # scope["state"], which BaseHTTPMiddleware does not
                    # reliably propagate to inner raw ASGI middleware).
                    owner = scope.get("_owner")

                    asyncio.create_task(
                        _write_request_log(
                            request_id=request_id,
                            owner=owner,
                            method=scope.get("method", ""),
                            path=path,
                            query=scope.get("query_string", b"").decode("latin-1") or None,
                            client_ip=_client_ip_from_scope(scope, raw_headers),
                            user_agent=raw_headers.get("user-agent"),
                            request_headers=safe_headers,
                            request_body=b"".join(body_chunks),
                            status_code=status_code,
                            response_headers=response_headers,
                            response_body=b"".join(response_chunks),
                            latency_ms=latency_ms,
                            log_bodies=settings.log_request_bodies,
                        )
                    )

            # Always forward the message to the actual client
            await send(message)

        await self.app(scope, receive_wrapper, send_wrapper)


async def _write_request_log(
    *,
    request_id: str,
    owner: str | None,
    method: str,
    path: str,
    query: str | None,
    client_ip: str,
    user_agent: str | None,
    request_headers: dict[str, str],
    request_body: bytes,
    status_code: int,
    response_headers: dict[str, str],
    response_body: bytes,
    latency_ms: int,
    log_bodies: bool,
) -> None:
    """
    Persist one request/response document to MongoDB request_logs collection.
    All errors are caught and logged — must never affect the request path.
    """
    try:
        from app.cache.zdr_cache import get_owner_zdr
        from app.db.mongo import get_mongo_db

        owner_zdr = await get_owner_zdr(owner) if owner else False
        effective_log_bodies = log_bodies and not owner_zdr
        if owner_zdr:
            logger.debug("zdr_bodies_suppressed", request_id=request_id, owner=owner)



        # ── Parse request body ────────────────────────────────────────────────
        request_body_doc = None
        if effective_log_bodies and request_body:
            content_type = request_headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    request_body_doc = json.loads(request_body)
                    # Never store API keys that may appear in body
                    if isinstance(request_body_doc, dict):
                        request_body_doc.pop("api_key", None)
                except (json.JSONDecodeError, ValueError):
                    request_body_doc = request_body.decode("utf-8", errors="replace")
            else:
                request_body_doc = request_body.decode("utf-8", errors="replace")[:10_000]

        # ── Parse response body ───────────────────────────────────────────────
        response_body_doc = None
        if effective_log_bodies and response_body:
            resp_content_type = response_headers.get("content-type", "")
            if "application/json" in resp_content_type:
                try:
                    response_body_doc = json.loads(response_body)
                except (json.JSONDecodeError, ValueError):
                    response_body_doc = response_body.decode("utf-8", errors="replace")
            elif "text/event-stream" in resp_content_type:
                # SSE stream: store as text, cap at 100 KB to avoid huge docs
                decoded = response_body.decode("utf-8", errors="replace")
                response_body_doc = decoded[:100_000] if len(decoded) > 100_000 else decoded
            else:
                response_body_doc = response_body.decode("utf-8", errors="replace")[:10_000]

        doc = {
            "_id": request_id,
            "ts": datetime.now(UTC),
            "method": method,
            "path": path,
            "query": query,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "owner": owner,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "request": {
                "headers": request_headers,
                "body": request_body_doc,
            },
            "response": {
                "headers": response_headers,
                "body": response_body_doc,
            },
        }

        db = get_mongo_db()
        await db.request_logs.insert_one(doc)

    except Exception as exc:  # noqa: BLE001
        logger.error("request_log_mongo_failed", request_id=request_id, error=str(exc))
