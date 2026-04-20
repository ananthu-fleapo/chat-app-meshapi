"""
OpenRouter provider adapter.

OpenRouter exposes an OpenAI-compatible API and routes to 200+ models
(GPT-4o, Claude, Mistral, Gemini, Llama, etc.) under one API key.
This is our sole upstream in Phase 1; later phases can add direct adapters.

Key responsibilities:
- Strip RouterV-only fields before forwarding (template, variables, session_id).
- Set `stream_options.include_usage = true` on streaming requests so the final
  SSE chunk carries token counts (needed by Phase 5 usage logger).
- Normalize upstream errors into RouterV's UpstreamError / GatewayTimeoutError.
- Manage a single shared httpx.AsyncClient (initialized at app startup).
"""

import json
from collections.abc import AsyncGenerator

import httpx
import structlog

from app.exceptions import GatewayTimeoutError, UnprocessableEntityError, UpstreamError
from app.providers.base import ProviderAdapter
from app.exceptions import _classify_openrouter_error
from app.schemas.chat import ROUTERV_ONLY_FIELDS, ChatCompletionRequest
from app.schemas.responses import RESPONSES_ONLY_FIELDS, ResponsesRequest
from app.schemas.embeddings import EmbeddingsRequest

logger = structlog.get_logger()


def _owner_user_label(owner: str | None) -> str | None:
    """Format the owner identifier for the upstream `user` field (≤256 chars)."""
    return f"owner:{owner}"[:256] if owner is not None else None


def _build_payload(
    request: ChatCompletionRequest,
    *,
    stream: bool,
    owner: str | None = None,
) -> dict:
    """
    Serialize the request for the upstream API.
    - Excludes None fields (avoids overriding upstream defaults with null).
    - Strips RouterV-only fields that must not reach the provider.
    - Forces stream=True/False explicitly.
    - Requests usage metadata in the final streaming chunk.
    - Sets user=owner:<label> for OpenRouter abuse-detection and analytics.
    """
    payload = request.model_dump(
        exclude_none=True,
        exclude=ROUTERV_ONLY_FIELDS,
    )
    payload["stream"] = stream
    if stream:
        # OpenRouter / OpenAI: include token counts in the final SSE chunk.
        payload.setdefault("stream_options", {})["include_usage"] = True
    # Stable per-owner identifier — OpenRouter uses this for abuse detection.
    # We use owner label (not key ID) so all keys for an owner share one bucket.
    if (label := _owner_user_label(owner)) is not None:
        payload.setdefault("user", label)
    return payload


def _build_embeddings_payload(
    request: EmbeddingsRequest,
    *,
    owner: str | None = None,
) -> dict:
    """
    Serialize an embeddings request for OpenRouter.

    The embeddings endpoint is non-streaming, so we only strip None values and
    apply the same `user` defaulting used for chat requests.
    """
    payload = request.model_dump(exclude_none=True)
    if (label := _owner_user_label(owner)) is not None:
        payload.setdefault("user", label)
    # OpenRouter requires `provider` to be an object. Callers may pass a bare
    # provider slug string as a convenience; normalise it here.
    if isinstance(payload.get("provider"), str):
        payload["provider"] = {"order": [payload["provider"]]}
    return payload


def _build_responses_payload(
    request: ResponsesRequest,
    *,
    stream: bool,
    owner: str | None = None,
    provider_model_id: str | None = None,
) -> dict:
    """
    Serialize a ResponsesRequest for the OpenRouter /responses endpoint.
    - Excludes None fields.
    - Strips RouterV-only fields (template, variables, session_id).
    - Forces stream=True/False explicitly.
    - Does NOT inject stream_options — the Responses API sends usage in the
      final SSE chunk natively, without needing include_usage=true.
    - Sets user=owner:<label> for OpenRouter abuse-detection.
    - Overrides model with provider_model_id when set (same pattern as _build_payload).
    """
    payload = request.model_dump(
        exclude_none=True,
        exclude=RESPONSES_ONLY_FIELDS,
    )
    payload["stream"] = stream
    if provider_model_id:
        payload["model"] = provider_model_id
    if owner is not None:
        payload.setdefault("user", f"owner:{owner}"[:256])
    return payload


class OpenRouterAdapter(ProviderAdapter):
    """Singleton adapter — one shared httpx client for the process lifetime."""

    _instance: "OpenRouterAdapter | None" = None

    def __init__(self, api_key: str, base_url: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                # OpenRouter uses these for analytics / rate-limit tiers.
                "HTTP-Referer": "https://routerv.com",
                "X-Title": "RouterV",
            },
            timeout=httpx.Timeout(timeout),
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @classmethod
    def init(
        cls, api_key: str, base_url: str, timeout: float = 120.0
    ) -> "OpenRouterAdapter":
        cls._instance = cls(api_key=api_key, base_url=base_url, timeout=timeout)
        logger.info("openrouter_adapter_ready", base_url=base_url)
        return cls._instance

    @classmethod
    def get(cls) -> "OpenRouterAdapter":
        if cls._instance is None:
            raise RuntimeError(
                "OpenRouterAdapter not initialized. Call OpenRouterAdapter.init() in lifespan."
            )
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        if cls._instance is not None:
            await cls._instance._client.aclose()
            cls._instance = None

    # ── ProviderAdapter interface ─────────────────────────────────────────────

    def _auth_headers(self, api_key: str | None) -> dict[str, str]:
        """
        Return per-request auth headers.

        When ``api_key`` is provided (owner has their own ProviderKey), it
        overrides the shared client's Authorization header for this request
        only.  httpx merges request-level headers over client defaults.
        """
        if api_key is not None:
            return {"Authorization": f"Bearer {api_key}"}
        return {}

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        payload = _build_payload(request, stream=False, owner=owner)
        if provider_model_id:
            payload["model"] = provider_model_id
        log = logger.bind(model=request.model)

        try:
            response = await self._client.post(
                "/chat/completions",
                json=payload,
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            log.warning(
                "upstream_http_error", status=exc.response.status_code, body=body[:300]
            )
            _classify_openrouter_error(exc.response.status_code, body)

        except httpx.TimeoutException as exc:
            log.warning("upstream_timeout", model=request.model)
            raise GatewayTimeoutError() from exc

    async def embeddings(
        self,
        request: EmbeddingsRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        payload = _build_embeddings_payload(request, owner=owner)
        if provider_model_id:
            payload["model"] = provider_model_id
        log = logger.bind(model=request.model)

        try:
            response = await self._client.post(
                "/embeddings",
                json=payload,
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            log.warning(
                "upstream_http_error", status=exc.response.status_code, body=body[:300]
            )
            _classify_openrouter_error(exc.response.status_code, body)

        except httpx.TimeoutException as exc:
            log.warning("upstream_timeout", model=request.model)
            raise GatewayTimeoutError() from exc

    async def stream_chat_completion(
        self,
        request: ChatCompletionRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        payload = _build_payload(request, stream=True, owner=owner)
        if provider_model_id:
            payload["model"] = provider_model_id
        log = logger.bind(model=request.model)

        try:
            async with self._client.stream(
                "POST",
                "/chat/completions",
                json=payload,
                headers=self._auth_headers(api_key),
            ) as response:
                if response.status_code >= 400:
                    # Read error body before the context manager closes the connection.
                    await response.aread()
                    body = response.text[:300]
                    log.warning(
                        "upstream_stream_error", status=response.status_code, body=body
                    )
                    _classify_openrouter_error(response.status_code, body)

                log.debug("upstream_stream_open")
                async for chunk in response.aiter_raw():
                    yield chunk

        except httpx.TimeoutException as exc:
            log.warning("upstream_stream_timeout")
            raise GatewayTimeoutError() from exc

    # ── Responses API ─────────────────────────────────────────────────────────

    async def responses_create(
        self,
        request: ResponsesRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        payload = _build_responses_payload(
            request, stream=False, owner=owner, provider_model_id=provider_model_id
        )
        log = logger.bind(model=request.model)

        try:
            response = await self._client.post(
                "/responses",
                json=payload,
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            log.warning(
                "upstream_http_error", status=exc.response.status_code, body=body
            )
            _classify_openrouter_error(exc.response.status_code, body)

        except httpx.TimeoutException as exc:
            log.warning("upstream_timeout", model=request.model)
            raise GatewayTimeoutError() from exc

    async def stream_responses_create(
        self,
        request: ResponsesRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        payload = _build_responses_payload(
            request, stream=True, owner=owner, provider_model_id=provider_model_id
        )
        log = logger.bind(model=request.model)

        try:
            async with self._client.stream(
                "POST",
                "/responses",
                json=payload,
                headers=self._auth_headers(api_key),
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    body = response.text[:300]
                    log.warning(
                        "upstream_stream_error", status=response.status_code, body=body
                    )
                    _classify_openrouter_error(response.status_code, body)

                log.debug("upstream_responses_stream_open")
                async for chunk in response.aiter_raw():
                    yield chunk

        except httpx.TimeoutException as exc:
            log.warning("upstream_responses_stream_timeout")
            raise GatewayTimeoutError() from exc
