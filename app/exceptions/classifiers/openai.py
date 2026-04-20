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

# ── HTTP classifier — OpenAI Direct ──────────────────────────────────────────


def _classify_openai_error(status: int, body: str) -> None:
    """
    Classify an OpenAI HTTP error.

    Documented statuses: 400, 401, 403, 404, 408, 409, 422, 429, 500, 503, 504

    400 sub-classification via error.code:
      context_length_exceeded → CONTEXT_WINDOW_EXCEEDED
      content_policy_violation / content_filter → CONTENT_POLICY_VIOLATION
      everything else → INVALID_REQUEST
    """
    from app.exceptions import (
        GatewayTimeoutError,
        UnprocessableEntityError,
        UpstreamError,
    )  # noqa: PLC0415

    try:
        error = json.loads(body).get("error") or {}
        error_code_field = str(error.get("code") or "")
        msg = (
            str(error.get("message") or "").strip()
            or "Your request could not be processed."
        )
        upstream_error: dict | None = {
            k: v for k, v in error.items() if k in ("type", "code", "message", "param")
        } or None
    except Exception:
        error_code_field = ""
        msg = "Your request could not be processed."
        upstream_error = None

    if status == 400:
        if error_code_field == "context_length_exceeded":
            pc = ProviderErrorCode.CONTEXT_WINDOW_EXCEEDED
        elif error_code_field in ("content_policy_violation", "content_filter"):
            pc = ProviderErrorCode.CONTENT_POLICY_VIOLATION
        else:
            pc = ProviderErrorCode.INVALID_REQUEST
        raise UnprocessableEntityError(
            msg, status_code=400, upstream_error=upstream_error, provider_code=pc
        )
    elif status == 422:
        raise UnprocessableEntityError(
            msg,
            status_code=422,
            upstream_error=upstream_error,
            provider_code=ProviderErrorCode.INVALID_REQUEST,
        )
    elif status in (408, 504):
        raise GatewayTimeoutError()
    elif status in (401, 403, 404, 409, 429, 500, 503):
        # 401: our key, 403: our permissions, 404: our model config,
        # 409: conflict, 429: our rate limit / quota, 500/503: provider down
        raise UpstreamError()
    else:
        raise UpstreamError()
