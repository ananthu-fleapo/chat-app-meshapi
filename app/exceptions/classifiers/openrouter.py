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

# ── HTTP classifier — OpenRouter ──────────────────────────────────────────────


def _classify_openrouter_error(status: int, body: str) -> None:
    """
    Classify an OpenRouter HTTP error.

    Documented statuses: 400, 401, 402, 403, 408, 429, 500, 502, 503

    402 = our credits exhausted → platform error (UpstreamError).
    403 = user's content moderation → user error (forwarded to client).
    """
    from app.exceptions import (
        GatewayTimeoutError,
        UnprocessableEntityError,
        UpstreamError,
    )  # noqa: PLC0415

    try:
        error = json.loads(body).get("error") or {}
        msg = (
            str(error.get("message") or "").strip()
            or "Your request could not be processed."
        )
        upstream_error: dict | None = {
            k: v for k, v in error.items() if k in ("code", "message", "metadata")
        } or None
    except Exception:
        msg = "Your request could not be processed."
        upstream_error = None

    if status == 400:
        raise UnprocessableEntityError(
            msg,
            status_code=400,
            upstream_error=upstream_error,
            provider_code=ProviderErrorCode.INVALID_REQUEST,
        )
    elif status == 403:
        raise UnprocessableEntityError(
            "Your request was blocked by content moderation.",
            status_code=403,
            upstream_error=upstream_error,
            provider_code=ProviderErrorCode.CONTENT_POLICY_VIOLATION,
        )
    elif status == 408:
        raise GatewayTimeoutError()
    elif status in (401, 402, 429, 500, 502, 503):
        # 401: our key, 402: our credits, 429: our rate limit, 5xx: provider down
        raise UpstreamError()
    else:
        raise UpstreamError()
