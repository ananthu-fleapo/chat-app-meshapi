from enum import Enum


class ProviderErrorCode(str, Enum):
    """
    Provider-agnostic error codes forwarded to clients on user-caused errors.
    Inheriting str makes the values JSON-serialisable without extra encoding.
    """

    # Auth
    INVALID_AUTH = "invalid_auth"
    PERMISSION_DENIED = "permission_denied"

    # Capacity
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    MONTHLY_QUOTA_EXCEEDED = "monthly_quota_exceeded"

    # Request content
    CONTEXT_WINDOW_EXCEEDED = "context_window_exceeded"
    CONTENT_POLICY_VIOLATION = "content_policy_violation"
    INVALID_REQUEST = "invalid_request"  # bad params / schema
    INVALID_INPUT = "invalid_input"  # bad data: invalid file, bad image, audio

    # Resource
    MODEL_NOT_FOUND = "model_not_found"
    RESOURCE_NOT_FOUND = "resource_not_found"

    # Provider health
    PROVIDER_OVERLOADED = "provider_overloaded"
    PROVIDER_TIMEOUT = "provider_timeout"
    CONNECTION_ERROR = "connection_error"
    INTERNAL_PROVIDER_ERROR = "internal_provider_error"  # 5xx from provider
    BAD_RESPONSE = "bad_response"  # HTTP 200 but unparseable body

    UNSUPPORTED_OPERATION = "unsupported_operation"

    # Fallback
    UNKNOWN = "unknown"
