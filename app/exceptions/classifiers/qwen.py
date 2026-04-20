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

# ── Qwen error-code → ProviderErrorCode patterns ─────────────────────────────

# Regex patterns (case-insensitive) for fine-grained Qwen sub-classification.
# Checked in order; first match wins.
_QWEN_CODE_PATTERNS: list[tuple[re.Pattern[str], ProviderErrorCode]] = [
    # Context / token limits
    (
        re.compile(
            r"invalid.?input.?length|input.?too.?long|context.?too.?long|token.?limit",
            re.I,
        ),
        ProviderErrorCode.CONTEXT_WINDOW_EXCEEDED,
    ),
    # Content policy
    (
        re.compile(r"data.?inspection.?failed|ip.?infringement", re.I),
        ProviderErrorCode.CONTENT_POLICY_VIOLATION,
    ),
    # Invalid input (files, images, URLs, audio)
    (
        re.compile(r"invalid.?file|invalid.?image|invalid.?url|^audio\.", re.I),
        ProviderErrorCode.INVALID_INPUT,
    ),
    # Missing / bad request structure
    (
        re.compile(r"invalid.?request|bad.?request|empty|missing", re.I),
        ProviderErrorCode.INVALID_REQUEST,
    ),
    # Unsupported features
    (
        re.compile(r"unsupported|not.?support", re.I),
        ProviderErrorCode.UNSUPPORTED_OPERATION,
    ),
    # Resource not found (user-side)
    (
        re.compile(r"not.?exist|not.?found", re.I),
        ProviderErrorCode.RESOURCE_NOT_FOUND,
    ),
    # Payload / size issues
    (
        re.compile(r"too.?large|payload|size.?exceed", re.I),
        ProviderErrorCode.INVALID_INPUT,
    ),
]

# Codes that indicate the 400 is the *user's* fault.
# Arrearage (billing overdue) is intentionally absent → UpstreamError.
_QWEN_USER_400_PREFIXES: tuple[str, ...] = (
    "InvalidParameter",
    "BadRequest",
    "InvalidFile",
    "InvalidImage",
    "InvalidURL",
    "DataInspectionFailed",
    "Audio.",
    "IPInfringementSuspect",
    "InvalidInputLength",
    "InvalidSchema",
    "ServiceUnavailableError",
    "UnsupportedOperation",
    "FlowNotPublished",
)

_QWEN_PLATFORM_400_PREFIXES = (
    "Arrearage",
    "Throttling",
    "APIConnectionError",
    "ClientDisconnect",
)


def _qwen_provider_code(code: str) -> ProviderErrorCode:
    """Return the most specific ProviderErrorCode for a Qwen error code string."""
    for pattern, pc in _QWEN_CODE_PATTERNS:
        if pattern.search(code):
            return pc
    return ProviderErrorCode.INVALID_REQUEST


# ── HTTP classifier — Qwen / DashScope ───────────────────────────────────────


def _classify_qwen_error(status: int, body: str) -> None:
    """
    Classify a Qwen / DashScope HTTP error.

    Documented statuses: 400, 401, 403, 404, 429, 430, 500, 503

    400 is split: user-error codes (InvalidParameter, InvalidInputLength, …) are
    forwarded; platform codes (Arrearage = our billing) are opaque UpstreamError.

    430 is a non-standard DashScope status for audio/file processing errors
    caused by the user's content.
    """
    from app.exceptions import (
        GatewayTimeoutError,
        UnprocessableEntityError,
        UpstreamError,
    )  # noqa: PLC0415

    try:
        parsed = json.loads(body)
        code = str(parsed.get("code") or parsed.get("error_code") or "")
        msg = (
            str(parsed.get("message") or "").strip()
            or "Your request could not be processed."
        )
        upstream_error: dict | None = {
            k: v for k, v in parsed.items() if k in ("code", "message", "request_id")
        } or None
    except Exception:
        code = ""
        msg = "Your request could not be processed."
        upstream_error = None

    if status == 400 and any(code.startswith(p) for p in _QWEN_USER_400_PREFIXES):
        raise UnprocessableEntityError(
            msg,
            status_code=400,
            upstream_error=upstream_error,
            provider_code=_qwen_provider_code(code),
        )
    elif status == 430:
        # Non-standard: audio / file processing errors
        raise UnprocessableEntityError(
            msg,
            status_code=430,
            upstream_error=upstream_error,
            provider_code=ProviderErrorCode.INVALID_INPUT,
        )
    elif status in (401, 403, 404, 429, 500, 503):
        # 401 InvalidApiKey (our key), 403 AccessDenied (our perms / model not purchased),
        # 404 model not found (our config), 429 Throttling.* (our quota),
        # 500 InternalError, 503 ModelUnavailable
        raise UpstreamError()
    else:
        raise UpstreamError()
