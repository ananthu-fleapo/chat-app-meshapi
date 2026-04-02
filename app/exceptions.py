"""
Custom exception hierarchy and FastAPI exception handlers.

All errors are serialized to the RouterV wire format:
  {
    "error": { "code": "...", "message": "..." },
    "request_id": "req_..."
  }

This overrides FastAPI's default 422 body so clients always get a consistent
error envelope regardless of where in the stack the error originated.

Logging policy
--------------
  5xx             → ERROR   (alerts should fire; operator action required)
  429             → WARNING (rate limiting working as intended; monitor trends)
  401 / 403       → WARNING (auth failures; spike may indicate abuse)
  other 4xx       → INFO    (client errors; not actionable by operator)
"""

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


# ── Base ─────────────────────────────────────────────────────────────────────

class RouterVError(Exception):
    """Base class for all RouterV application errors."""
    status_code: int = 500
    error_code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.message = message or self.__class__.message
        super().__init__(self.message)


# ── 4xx ──────────────────────────────────────────────────────────────────────

class UnauthorizedError(RouterVError):
    status_code = 401
    error_code = "unauthorized"
    message = "Invalid or missing API key."


class PaymentRequiredError(RouterVError):
    status_code = 402
    error_code = "spend_limit_exceeded"
    message = "Spend cap reached. Add credits or increase your spend limit."


class ForbiddenError(RouterVError):
    status_code = 403
    error_code = "forbidden"
    message = "Access denied."


class NotFoundError(RouterVError):
    status_code = 404
    error_code = "not_found"
    message = "Resource not found."


class UnsupportedModelError(RouterVError):
    status_code = 404
    error_code = "model_not_found"
    message = "Model not found or not supported."

    def __init__(self, model: str | None = None) -> None:
        msg = f"Model '{model}' is not supported." if model else self.__class__.message
        super().__init__(msg)


class UnprocessableEntityError(RouterVError):
    status_code = 422
    error_code = "unprocessable_entity"
    message = "Request could not be processed."


class RateLimitError(RouterVError):
    status_code = 429
    error_code = "rate_limit_exceeded"
    message = "Rate limit exceeded."

    def __init__(
        self,
        message: str | None = None,
        limit_type: str = "rpm",
        retry_after: int = 60,
    ) -> None:
        super().__init__(message)
        self.limit_type = limit_type
        self.retry_after = retry_after


# ── 5xx ──────────────────────────────────────────────────────────────────────

class UpstreamError(RouterVError):
    status_code = 500
    error_code = "upstream_error"
    message = "Upstream provider returned an error."


class GatewayTimeoutError(RouterVError):
    status_code = 500
    error_code = "gateway_timeout"
    message = "Upstream provider did not respond in time."


# ── Handlers ─────────────────────────────────────────────────────────────────

def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


async def routerv_exception_handler(request: Request, exc: RouterVError) -> JSONResponse:
    rid = _request_id(request)

    # ── Structured logging by severity ───────────────────────────────────────
    log_fields: dict = {
        "error_code": exc.error_code,
        "status_code": exc.status_code,
        "path": request.url.path,
        "method": request.method,
    }

    if exc.status_code >= 500:
        # 5xx: operator action likely required — alert should fire.
        logger.error("request_error", error_message=exc.message, **log_fields)

    elif exc.status_code == 429:
        # Rate limit: expected under normal load, but a spike means abuse.
        extra: dict = {}
        if isinstance(exc, RateLimitError):
            extra = {"limit_type": exc.limit_type, "retry_after": exc.retry_after}
        logger.warning("rate_limit_exceeded", **log_fields, **extra)

    elif exc.status_code in (401, 403):
        # Auth failure: a sustained spike could indicate credential brute-force.
        logger.warning("auth_error", **log_fields)

    else:
        # Other 4xx: client error, not actionable by operator.
        logger.info("client_error", error_message=exc.message, **log_fields)

    # ── Wire response ─────────────────────────────────────────────────────────
    headers: dict[str, str] = {}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
            },
            "request_id": rid,
        },
        headers=headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.info(
        "validation_error",
        path=request.url.path,
        method=request.method,
        detail=exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed.",
                "details": exc.errors(),
            },
            "request_id": _request_id(request),
        },
    )
