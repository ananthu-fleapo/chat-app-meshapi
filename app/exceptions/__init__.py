# ── Base error hierarchy ─────────────────────────────────────────────

from .base import (
    RouterVError,
)

# ── 4xx errors ───────────────────────────────────────────────────────

from .base import (
    UnauthorizedError,
    PaymentRequiredError,
    ForbiddenError,
    NotFoundError,
    UnsupportedModelError,
    ModelCapabilityError,
    UnprocessableEntityError,
    RateLimitError,
)

# ── 5xx errors ───────────────────────────────────────────────────────

from .base import (
    ProviderNotAvailableError,
    UpstreamError,
    GatewayTimeoutError,
    AutoRouterMisconfiguredError,
)

# ── Provider error codes ─────────────────────────────────────────────

from .codes import ProviderErrorCode

# ── Exception handlers (FastAPI) ─────────────────────────────────────

from .base import (
    routerv_exception_handler,
    validation_exception_handler,
)

# -- Clasifiers --

from .classifiers.qwen import _classify_qwen_error
from .classifiers.bedrock import _classify_bedrock_http_error
from .classifiers.bedrock import _raise_bedrock_exc
from .classifiers.openrouter import _classify_openrouter_error
from .classifiers.vertex import _classify_vertex_error
from .classifiers.openai import _classify_openai_error
