"""
OpenAI Direct provider adapter.

A thin wrapper around the OpenAI API — same JSON format as OpenRouter so we
reuse the payload builder and httpx client pattern.

Differences from OpenRouterAdapter
------------------------------------
- Base URL: settings.openai_base_url  (default: https://api.openai.com/v1)
- Auth: settings.openai_api_key (system default; per-owner key supported via DB)
- Model translation: strip the "openai/" prefix that RouterV uses canonically
  (e.g. "openai/gpt-4o" → "gpt-4o").
- No per-request OpenRouter analytics headers.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
import structlog

from app.exceptions import GatewayTimeoutError, UpstreamError
from app.providers.base import ProviderAdapter
from app.providers.openrouter import _build_payload
from app.schemas.chat import ChatCompletionRequest

logger = structlog.get_logger()


def _openai_model_id(canonical: str) -> str:
    """
    Translate a canonical RouterV model name to an OpenAI model ID.
    Strips the "openai/" namespace prefix that RouterV adds.
    """
    if canonical.startswith("openai/"):
        return canonical[len("openai/"):]
    return canonical


class OpenAIDirectAdapter(ProviderAdapter):
    """Singleton adapter — one shared httpx client for the process lifetime."""

    _instance: "OpenAIDirectAdapter | None" = None

    def __init__(self, api_key: str, base_url: str, timeout: float) -> None:
        self._default_api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout),
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @classmethod
    def init(
        cls, api_key: str, base_url: str, timeout: float = 120.0
    ) -> "OpenAIDirectAdapter":
        cls._instance = cls(api_key=api_key, base_url=base_url, timeout=timeout)
        logger.info("openai_direct_adapter_ready", base_url=base_url)
        return cls._instance

    @classmethod
    def get(cls) -> "OpenAIDirectAdapter":
        if cls._instance is None:
            raise RuntimeError(
                "OpenAIDirectAdapter not initialized. "
                "Call OpenAIDirectAdapter.init() in lifespan."
            )
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        if cls._instance is not None:
            await cls._instance._client.aclose()
            cls._instance = None

    # ── ProviderAdapter interface ─────────────────────────────────────────────

    def _auth_headers(self, api_key: str | None) -> dict[str, str]:
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
        payload["model"] = provider_model_id or _openai_model_id(payload["model"])
        log = logger.bind(model=request.model, openai_model=payload["model"])

        try:
            response = await self._client.post(
                "/chat/completions",
                json=payload,
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            log.warning("openai_direct_http_error", status=exc.response.status_code, body=body)
            raise UpstreamError() from exc

        except httpx.TimeoutException as exc:
            log.warning("openai_direct_timeout")
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
        payload["model"] = provider_model_id or _openai_model_id(payload["model"])
        log = logger.bind(model=request.model, openai_model=payload["model"])

        try:
            async with self._client.stream(
                "POST",
                "/chat/completions",
                json=payload,
                headers=self._auth_headers(api_key),
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    body = response.text[:300]
                    log.warning(
                        "openai_direct_stream_error",
                        status=response.status_code,
                        body=body,
                    )
                    raise UpstreamError()

                log.debug("openai_direct_stream_open")
                async for chunk in response.aiter_raw():
                    yield chunk

        except httpx.TimeoutException as exc:
            log.warning("openai_direct_stream_timeout")
            raise GatewayTimeoutError() from exc
