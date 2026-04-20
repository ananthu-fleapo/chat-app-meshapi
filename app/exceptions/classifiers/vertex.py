"""
Unified Provider Error Classifier
===================================
Single source of truth for mapping provider HTTP errors (and Bedrock SDK
exceptions) to RouterV's typed exception hierarchy.

Design rules
------------
1. If the provider returns a status code the **user** caused → forward that
   exact status code to the client.
2. HTTP 422 `UnprocessableEntityError` is the **fallback** only when we have
   a user error but no precise status available.
3. HTTP 500 `UpstreamError` is reserved for **platform failures** — our key,
   our billing, our quota, or the provider being down.  No detail forwarded.
4. Provider message is always included in `upstream_error` for user errors so
   the caller can act on it.
5. Platform errors are opaque: no provider message reaches the client.

HTTP classifier signatures
--------------------------
All `_classify_*_error(status, body)` functions return None and always raise.
They are the only place where RouterV exceptions are constructed for provider
errors; the adapter files just call them.

References
----------
- OpenRouter:  https://openrouter.ai/docs/api/reference/errors-and-debugging
- OpenAI:      https://platform.openai.com/docs/guides/error-codes
- Vertex AI:   https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/api-errors
- Qwen:        https://www.alibabacloud.com/help/en/model-studio/error-code
- Bedrock:     https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html
"""

from __future__ import annotations

import json
import re
from enum import Enum

from app.exceptions import ProviderErrorCode


# ── HTTP classifier — Vertex AI ───────────────────────────────────────────────


def _classify_vertex_error(status: int, body: str) -> None:
    """
    Classify a Vertex AI HTTP error.

    gRPC → HTTP mapping:
      INVALID_ARGUMENT     → 400  (user: bad params, context too long)
      FAILED_PRECONDITION  → 400  (platform: billing not enabled, model not allowlisted)
      UNAUTHENTICATED      → 401  (platform: our service account key)
      PERMISSION_DENIED    → 403  (platform: our IAM roles)
      NOT_FOUND            → 404  (platform: our model config)
      RESOURCE_EXHAUSTED   → 429  (platform: our quota / rate limit)
      CANCELLED            → 499  (platform)
      INTERNAL / UNKNOWN   → 500  (platform: provider down)
      UNAVAILABLE          → 503  (platform)
      DEADLINE_EXCEEDED    → 504  (timeout)
    """
    from app.exceptions import (
        GatewayTimeoutError,
        UnprocessableEntityError,
        UpstreamError,
    )  # noqa: PLC0415

    try:
        error = json.loads(body).get("error") or {}
        error_status = str(error.get("status") or "")
        msg = (
            str(error.get("message") or "").strip()
            or "Your request could not be processed."
        )
        upstream_error: dict | None = {
            k: v for k, v in error.items() if k in ("code", "status", "message")
        } or None
    except Exception:
        error_status = ""
        msg = "Your request could not be processed."
        upstream_error = None

    if error_status == "INVALID_ARGUMENT":
        msg_lower = msg.lower()
        if any(kw in msg_lower for kw in ("token", "context", "length", "too long")):
            pc = ProviderErrorCode.CONTEXT_WINDOW_EXCEEDED
        else:
            pc = ProviderErrorCode.INVALID_REQUEST
        raise UnprocessableEntityError(
            msg, status_code=400, upstream_error=upstream_error, provider_code=pc
        )
    elif error_status == "DEADLINE_EXCEEDED" or status == 504:
        raise GatewayTimeoutError()
    elif status in (400, 401, 403, 404, 429, 499, 500, 503):
        # 400 FAILED_PRECONDITION: model not allowlisted / billing not enabled (our config)
        # 401 UNAUTHENTICATED: our service account
        # 403 PERMISSION_DENIED: our IAM
        # 404 NOT_FOUND: our model config
        # 429 RESOURCE_EXHAUSTED: our quota
        # 499 CANCELLED, 500 INTERNAL/UNKNOWN, 503 UNAVAILABLE
        raise UpstreamError()
    else:
        raise UpstreamError()
