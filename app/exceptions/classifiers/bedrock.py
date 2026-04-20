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

# ── Bedrock HTTP path — known user-caused __type values ──────────────────────

# 400 __type values where the fault is clearly the user's request content or schema.
# Notes:
#   - AWS docs list both "ValidationError" and "ValidationException" as separate 400 errors;
#     both are user-caused.
#   - "MalformedHttpRequest" and its long-form "MalformedHttpRequestException" are both
#     observed in the wild depending on the Bedrock sub-service.
#   - "RequestAbortedException" (400) is a client-cancelled / connection-dropped event —
#     treated as a platform/infrastructure issue (→ UpstreamError), not a user error.
#   - "ThrottlingException" at 400 is our quota limit → UpstreamError.
#   - "IncompleteSignature" at 400 is our signing code / credentials → UpstreamError.
_BEDROCK_USER_400_TYPES: frozenset[str] = frozenset(
    {
        "ValidationException",
        "ValidationError",
        "MalformedHttpRequest",
        "MalformedHttpRequestException",
    }
)


# ── HTTP classifier — Bedrock bearer path ────────────────────────────────────


def _classify_bedrock_http_error(status: int, body: str) -> None:
    """
    Classify a Bedrock HTTP error (bearer/REST path).

    Replaces the six identical inline `if resp.status_code == 400` blocks
    scattered across BedrockAdapter's private methods.

    Bedrock error body shape: {"__type": "ExceptionClassName", "message": "..."}

    Documented statuses: 400, 401, 403, 404, 408, 413, 424, 429, 500, 503

    400 split (user → forwarded, platform → opaque):
      ValidationException / ValidationError         → user
      MalformedHttpRequest / MalformedHttpRequestException → user
      ThrottlingException                            → platform (our quota)
      IncompleteSignature                            → platform (our signing code)
      RequestAbortedException                        → platform (client dropped)

    401 NotAuthorized                          → platform (our IAM)
    403 AccessDeniedException / ExpiredTokenException /
        IncompleteSignature / OptInRequired /
        UnrecognizedClientException            → platform (our auth)
    404 UnknownOperationException              → platform (our API call)
    408 RequestTimeoutException                → GatewayTimeoutError
    413 RequestEntityTooLargeException         → user (payload too large)
    424 ModelNotReadyException                 → platform (Bedrock auto-retries)
    429 ThrottlingException                    → platform (our quota)
    500 InternalFailure                        → platform
    503 ServiceUnavailable                     → platform
    """
    from app.exceptions import (
        GatewayTimeoutError,
        UnprocessableEntityError,
        UpstreamError,
    )  # noqa: PLC0415

    try:
        parsed = json.loads(body)
        msg = (
            str(parsed.get("message") or parsed.get("Message") or "").strip()
            or "Your request could not be processed."
        )
        exc_type = str(parsed.get("__type") or "")
        upstream_error = {
            k: v
            for k, v in {
                "type": parsed.get("__type"),
                "message": parsed.get("message") or parsed.get("Message"),
            }.items()
            if v is not None
        } or None
    except Exception:
        msg = "Your request could not be processed."
        exc_type = ""
        upstream_error = None

    if status == 400:
        if exc_type in _BEDROCK_USER_400_TYPES:
            raise UnprocessableEntityError(
                msg,
                status_code=400,
                upstream_error=upstream_error,
                provider_code=ProviderErrorCode.INVALID_REQUEST,
            )
        # ThrottlingException at 400, IncompleteSignature, etc. → platform
        raise UpstreamError()
    elif status == 413:
        raise UnprocessableEntityError(
            msg,
            status_code=413,
            upstream_error=upstream_error,
            provider_code=ProviderErrorCode.INVALID_INPUT,
        )
    elif status == 408:
        raise GatewayTimeoutError()
    elif status in (401, 403, 404, 424, 429, 500, 503):
        # 401/403: our auth, 404: our model ARN config, 424: model not ready (platform),
        # 429: our quota, 500/503: provider down
        raise UpstreamError()
    else:
        raise UpstreamError()


# ── SDK classifier — Bedrock aiobotocore path ─────────────────────────────────


def _raise_bedrock_exc(exc: Exception, log: object, context: str) -> None:
    """
    Convert a raw Bedrock / aiobotocore SDK exception to a typed RouterV exception.

    Called from BedrockAdapter's `except Exception` blocks when using SigV4 auth.
    Platform errors are logged with specific event names so ops can triage by type.

    Exception type detection uses string matching against the class name because
    aiobotocore exceptions are dynamically generated from service models and do
    not have stable importable types.
    """
    from app.exceptions import (
        GatewayTimeoutError,
        UnprocessableEntityError,
        UpstreamError,
    )  # noqa: PLC0415

    err_str = str(exc)
    err_name = type(exc).__name__

    # User error: bad parameters / invalid model configuration
    if "ValidationException" in err_str or "ValidationException" in err_name:
        log.warning(f"bedrock_validation_error_{context}", error=err_str)  # type: ignore[union-attr]
        raise UnprocessableEntityError(
            err_str, provider_code=ProviderErrorCode.INVALID_REQUEST
        ) from exc

    # Timeout: model took too long or underlying I/O timed out
    if (
        "ModelTimeoutException" in err_name
        or "Timeout" in err_name
        or "timeout" in err_str.lower()
    ):
        log.warning(f"bedrock_timeout_{context}")  # type: ignore[union-attr]
        raise GatewayTimeoutError() from exc

    # Platform errors — log with specific event names for ops visibility
    if "AccessDeniedException" in err_name:
        log.error(f"bedrock_access_denied_{context}", error=err_str)  # type: ignore[union-attr]
    elif "ServiceQuotaExceededException" in err_name:
        log.warning(f"bedrock_quota_exceeded_{context}", error=err_str)  # type: ignore[union-attr]
    elif "ThrottlingException" in err_name:
        log.warning(f"bedrock_throttled_{context}", error=err_str)  # type: ignore[union-attr]
    elif "ModelNotReadyException" in err_name:
        log.warning(f"bedrock_model_not_ready_{context}", error=err_str)  # type: ignore[union-attr]
    elif "ModelErrorException" in err_name:
        log.error(f"bedrock_model_error_{context}", error=err_str)  # type: ignore[union-attr]
    elif "ResourceNotFoundException" in err_name:
        log.error(f"bedrock_resource_not_found_{context}", error=err_str)  # type: ignore[union-attr]
    elif "InternalServerException" in err_name:
        log.error(f"bedrock_internal_server_{context}", error=err_str)  # type: ignore[union-attr]
    elif "ServiceUnavailableException" in err_name:
        log.warning(f"bedrock_service_unavailable_{context}", error=err_str)  # type: ignore[union-attr]
    elif "ModelStreamErrorException" in err_name:
        log.error(f"bedrock_stream_error_{context}", error=err_str)  # type: ignore[union-attr]
    else:
        log.warning(f"bedrock_error_{context}", error=err_str)  # type: ignore[union-attr]

    raise UpstreamError() from exc
