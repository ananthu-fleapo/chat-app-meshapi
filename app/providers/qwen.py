"""
Qwen (Alibaba Cloud) direct provider adapter.

Qwen models are served through the DashScope API, which exposes an
OpenAI-compatible REST endpoint.  This adapter is structurally identical
to OpenAIDirectAdapter — it reuses the same payload builder and httpx
client pattern with a different base URL and API key.

Endpoint
--------
https://dashscope.aliyuncs.com/compatible-mode/v1

Model translation
-----------------
RouterV canonical names use the "qwen/" namespace prefix.
DashScope expects bare model names (e.g. "qwen-turbo", "qwen-max").
The adapter strips the "qwen/" prefix before forwarding.

Example canonical → DashScope:
  "qwen/qwen-turbo"         → "qwen-turbo"
  "qwen/qwen-plus"          → "qwen-plus"
  "qwen/qwen-max"           → "qwen-max"
  "qwen/qwen-long"          → "qwen-long"
  "qwen/qwen2.5-72b-instruct" → "qwen2.5-72b-instruct"
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
import structlog

from app.exceptions import GatewayTimeoutError, UpstreamError
from app.providers.base import ProviderAdapter
from app.providers.openrouter import _build_payload
from app.schemas.chat import ChatCompletionRequest
from app.schemas.responses import RESPONSES_ONLY_FIELDS, ResponsesRequest
from app.schemas.embeddings import EmbeddingsRequest

logger = structlog.get_logger()

# DashScope OpenAI-compatible endpoint (text embeddings + chat)
_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _qwen_model_id(canonical: str) -> str:
    """
    Translate a canonical RouterV model name to a DashScope model ID.
    Strips the "qwen/" namespace prefix.
    """
    if canonical.startswith("qwen/"):
        return canonical[len("qwen/"):]
    return canonical


def _qwen_text_type(input_type: str | None) -> str | None:
    """
    Map input_type to Qwen text_type.
    Qwen only supports 'query' and 'document' (default).
    """
    if input_type in ("query", "document"):
        return input_type
    return None


class QwenAdapter(ProviderAdapter):
    """
    Singleton adapter for Qwen models via the DashScope OpenAI-compatible API.
    """

    _instance: "QwenAdapter | None" = None

    def __init__(self, api_key: str, base_url: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout),
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @classmethod
    def init(
        cls,
        api_key: str,
        base_url: str = _DASHSCOPE_BASE_URL,
        timeout: float = 120.0,
    ) -> "QwenAdapter":
        cls._instance = cls(api_key=api_key, base_url=base_url, timeout=timeout)
        logger.info("qwen_adapter_ready", base_url=base_url)
        return cls._instance

    @classmethod
    def get(cls) -> "QwenAdapter":
        if cls._instance is None:
            raise RuntimeError(
                "QwenAdapter not initialized. Call QwenAdapter.init() in lifespan."
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
        payload["model"] = provider_model_id or _qwen_model_id(payload["model"])
        # Qwen3/QwQ models have thinking enabled by default; DashScope rejects
        # non-streaming requests unless enable_thinking is explicitly false.
        payload["enable_thinking"] = False
        log = logger.bind(model=request.model, qwen_model=payload["model"])

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
            log.warning("qwen_http_error", status=exc.response.status_code, body=body)
            raise UpstreamError() from exc

        except httpx.TimeoutException as exc:
            log.warning("qwen_timeout")
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
        payload["model"] = provider_model_id or _qwen_model_id(payload["model"])
        log = logger.bind(model=request.model, qwen_model=payload["model"])

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
                    log.warning("qwen_stream_error", status=response.status_code, body=body)
                    raise UpstreamError()

                log.debug("qwen_stream_open")
                async for chunk in response.aiter_raw():
                    yield chunk

        except httpx.TimeoutException as exc:
            log.warning("qwen_stream_timeout")
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
        payload = request.model_dump(exclude_none=True, exclude=RESPONSES_ONLY_FIELDS)
        payload["stream"] = False
        payload["model"] = provider_model_id or _qwen_model_id(payload.get("model", ""))
        payload["enable_thinking"] = False
        if owner is not None:
            payload.setdefault("user", f"owner:{owner}"[:256])
        if "response_format" in payload:
            payload["text"] = {"format": payload.pop("response_format")}
        log = logger.bind(model=request.model, qwen_model=payload["model"])

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
            log.warning("qwen_responses_http_error", status=exc.response.status_code, body=body)
            raise UpstreamError() from exc

        except httpx.TimeoutException as exc:
            log.warning("qwen_responses_timeout")
            raise GatewayTimeoutError() from exc

    async def stream_responses_create(
        self,
        request: ResponsesRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        payload = request.model_dump(exclude_none=True, exclude=RESPONSES_ONLY_FIELDS)
        payload["stream"] = True
        payload["model"] = provider_model_id or _qwen_model_id(payload.get("model", ""))
        if owner is not None:
            payload.setdefault("user", f"owner:{owner}"[:256])
        if "response_format" in payload:
            payload["text"] = {"format": payload.pop("response_format")}
        log = logger.bind(model=request.model, qwen_model=payload["model"])

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
                    log.warning("qwen_responses_stream_error", status=response.status_code, body=body)
                    raise UpstreamError()

                log.debug("qwen_responses_stream_open")
                async for chunk in response.aiter_raw():
                    yield chunk

        except httpx.TimeoutException as exc:
            log.warning("qwen_responses_stream_timeout")
            raise GatewayTimeoutError() from exc


    async def embeddings(
        self,
        request: EmbeddingsRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        from app.providers.openrouter import _owner_user_label

        model_id = provider_model_id or _qwen_model_id(request.model)
        log = logger.bind(model=request.model, qwen_model=model_id)

        try:
            payload = request.model_dump(exclude_none=True, exclude={"model", "provider", "input_type"})
            payload["model"] = model_id
            if (label := _owner_user_label(owner)) is not None:
                payload.setdefault("user", label)
            # Qwen uses 'text_type' (not 'input_type') with values 'query' or 'document'
            if (text_type := _qwen_text_type(request.input_type)) is not None:
                payload["text_type"] = text_type
            response = await self._client.post(
                "/embeddings",
                json=payload,
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            log.warning("qwen_embed_http_error", status=exc.response.status_code, body=body[:300])
            raise UpstreamError(upstream_detail=body) from exc

        except httpx.TimeoutException as exc:
            log.warning("qwen_embed_timeout")
            raise GatewayTimeoutError() from exc