import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from ulid import ULID

logger = structlog.get_logger()

# Paths exempt from the Cloudflare origin guard — Cloud Run health probes
# are called directly by the GCP load balancer, not via Cloudflare.
_CF_EXEMPT_PATHS = {"/healthz", "/readyz"}


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
                    client=request.client.host if request.client else "unknown",
                )
                return Response(
                    content='{"error":{"code":"forbidden","message":"Forbidden"}}',
                    status_code=403,
                    media_type="application/json",
                )

        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique request ID to every inbound request.

    - Honors an existing `X-Request-Id` header (pass-through for upstream tracing).
    - Generates a ULID-based ID if none is provided: `req_<ulid>`.
    - Stores the ID on `request.state.request_id` for use in handlers/services.
    - Binds it to structlog's contextvars so every log line within the request
      automatically carries `request_id=...` without manual passing.
    - Echoes the ID back in the `X-Request-Id` response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or f"req_{ULID()}"
        request.state.request_id = request_id

        # Clear any stale context from a previous request on this coroutine,
        # then bind the new request ID for all log calls within this scope.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
