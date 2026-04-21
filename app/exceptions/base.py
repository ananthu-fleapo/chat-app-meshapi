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

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from app.exceptions.codes import ProviderErrorCode

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
        msg = f"Model '{model}' is not supported or is invalid." if model else self.__class__.message
        super().__init__(msg)


class ModelCapabilityError(RouterVError):
    status_code = 400
    error_code = "model_capability_not_supported"
    message = "This model does not support the requested API."

    def __init__(self, model: str, api: str) -> None:
        super().__init__(f"Model '{model}' does not support the {api} API.")


class UnprocessableEntityError(RouterVError):
    status_code = 422
    error_code = "unprocessable_entity"
    message = "Request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        upstream_error: dict | None = None,
        provider_code: "ProviderErrorCode | None" = None,
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.upstream_error = upstream_error
        self.provider_code = provider_code


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


class ProviderNotAvailableError(RouterVError):
    """
    A provider slug is configured in model_prices but its adapter is not
    registered — meaning the required credentials (e.g. GOOGLE_PROJECT_ID)
    are missing from the server environment.  This is a server-side config
    error, not a user error, so it returns 503.
    """

    status_code = 503
    error_code = "provider_not_available"
    message = "The upstream provider for this model is not available."

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Provider '{provider}' is not available. "
            "The required credentials may not be configured on this server."
        )


class UpstreamError(RouterVError):
    status_code = 500
    error_code = "upstream_error"
    message = "Upstream provider returned an error."

    def __init__(self, upstream_detail: str | None = None) -> None:
        super().__init__()
        self.upstream_detail = upstream_detail


class GatewayTimeoutError(RouterVError):
    status_code = 500
    error_code = "gateway_timeout"
    message = "Upstream provider did not respond in time."


# ── Handlers ─────────────────────────────────────────────────────────────────


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


async def routerv_exception_handler(
    request: Request, exc: RouterVError
) -> JSONResponse:
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

    error_body: dict = {"code": exc.error_code, "message": exc.message}
    if isinstance(exc, UpstreamError) and exc.upstream_detail:
        # Truncate to first 500 chars to avoid leaking provider metadata (account IDs, quotas, etc.)
        error_body["upstream_detail"] = exc.upstream_detail[:500]
    if isinstance(exc, UnprocessableEntityError):
        if exc.upstream_error:
            error_body["upstream_error"] = exc.upstream_error
        if exc.provider_code is not None:
            error_body["provider_code"] = exc.provider_code.value

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_body, "request_id": rid},
        headers=headers,
    )


def _serialize_validation_errors(errors: list) -> list:
    """Convert Pydantic v2 error dicts to JSON-serializable form.

    Pydantic v2 includes the original Python exception in ctx.error, which
    is not JSON-serializable by json.dumps. Convert exceptions to strings.
    """
    out = []
    for err in errors:
        e = dict(err)
        if "ctx" in e:
            e["ctx"] = {
                k: str(v) if isinstance(v, Exception) else v
                for k, v in e["ctx"].items()
            }
        e.pop("url", None)  # strip verbose Pydantic docs URL
        out.append(e)
    return out


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = _serialize_validation_errors(exc.errors())
    logger.info(
        "validation_error",
        path=request.url.path,
        method=request.method,
        detail=errors,
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed.",
                "details": errors,
            },
            "request_id": _request_id(request),
        },
    )
