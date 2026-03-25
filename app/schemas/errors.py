"""
RouterV error wire format (Pydantic models).

All error responses conform to:
  {
    "error": {
      "code": "rate_limit_exceeded",
      "message": "...",
      ...
    },
    "request_id": "req_01J..."
  }

This mirrors the OpenAI error envelope closely so existing SDK integrations
that inspect `response.error` continue to work with zero changes.
"""

from pydantic import BaseModel


class ProviderError(BaseModel):
    """Upstream provider error forwarded for debugging."""
    provider: str
    status: int | None = None
    message: str | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    param: str | None = None
    details: list | None = None           # validation error list
    provider_error: ProviderError | None = None
    retry_after_seconds: int | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
    request_id: str = ""
