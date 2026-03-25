import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from ulid import ULID

logger = structlog.get_logger()


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
