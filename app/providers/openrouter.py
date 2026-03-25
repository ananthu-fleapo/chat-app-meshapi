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

from collections.abc import AsyncGenerator

import httpx
import structlog

from app.exceptions import GatewayTimeoutError, UpstreamError
from app.providers.base import ProviderAdapter
from app.schemas.chat import ROUTERV_ONLY_FIELDS, ChatCompletionRequest

logger = structlog.get_logger()


def _build_payload(request: ChatCompletionRequest, *, stream: bool) -> dict:
    """
    Serialize the request for the upstream API.
    - Excludes None fields (avoids overriding upstream defaults with null).
    - Strips RouterV-only fields that must not reach the provider.
    - Forces stream=True/False explicitly.
    - Requests usage metadata in the final streaming chunk.
    """
    payload = request.model_dump(
        exclude_none=True,
        exclude=ROUTERV_ONLY_FIELDS,
    )
    payload["stream"] = stream
    if stream:
        # OpenRouter / OpenAI: include token counts in the final SSE chunk.
        payload.setdefault("stream_options", {})["include_usage"] = True
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
    def init(cls, api_key: str, base_url: str, timeout: float = 120.0) -> "OpenRouterAdapter":
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

    async def chat_completion(self, request: ChatCompletionRequest) -> dict:
        payload = _build_payload(request, stream=False)
        log = logger.bind(model=request.model)

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            log.warning("upstream_http_error", status=exc.response.status_code, body=body)
            raise UpstreamError(
                f"Upstream returned {exc.response.status_code}: {body}"
            ) from exc

        except httpx.TimeoutException as exc:
            log.warning("upstream_timeout", model=request.model)
            raise GatewayTimeoutError() from exc

    async def stream_chat_completion(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[bytes, None]:
        payload = _build_payload(request, stream=True)
        log = logger.bind(model=request.model)

        try:
            async with self._client.stream(
                "POST", "/chat/completions", json=payload
            ) as response:
                if response.status_code >= 400:
                    # Read error body before the context manager closes the connection.
                    await response.aread()
                    body = response.text[:300]
                    log.warning("upstream_stream_error", status=response.status_code, body=body)
                    raise UpstreamError(
                        f"Upstream returned {response.status_code}: {body}"
                    )

                log.debug("upstream_stream_open")
                async for chunk in response.aiter_raw():
                    yield chunk

        except httpx.TimeoutException as exc:
            log.warning("upstream_stream_timeout")
            raise GatewayTimeoutError() from exc
