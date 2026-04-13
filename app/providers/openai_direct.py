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
from app.schemas.responses import RESPONSES_ONLY_FIELDS, ResponsesRequest
from app.schemas.embeddings import EmbeddingsRequest

logger = structlog.get_logger()


def _build_responses_payload(
    request: ResponsesRequest,
    *,
    stream: bool,
    owner: str | None = None,
    provider_model_id: str | None = None,
) -> dict:
    """
    Serialize a ResponsesRequest for the OpenAI /responses endpoint.
    - OpenAI wraps response_format as: {"text": {"format": <original>}}.
    - model is set from provider_model_id or stripped of the "openai/" prefix.
    - Does NOT inject stream_options — OpenAI Responses API sends usage natively.
    """
    payload = request.model_dump(exclude_none=True, exclude=RESPONSES_ONLY_FIELDS)
    payload["stream"] = stream
    payload["model"] = provider_model_id or _openai_model_id(payload.get("model", ""))
    if "response_format" in payload:
        payload["text"] = {"format": payload.pop("response_format")}
    if owner is not None:
        payload.setdefault("user", f"owner:{owner}"[:256])
    return payload


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
        if "max_tokens" in payload:
            payload["max_completion_tokens"] = payload.pop("max_tokens")
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
        if "max_tokens" in payload:
            payload["max_completion_tokens"] = payload.pop("max_tokens")
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

    # ── Batch / Files API ─────────────────────────────────────────────────────

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        purpose: str,
        *,
        api_key: str | None = None,
    ) -> dict:
        try:
            response = await self._client.post(
                "/files",
                files={"file": (filename, file_bytes, "application/octet-stream")},
                data={"purpose": purpose},
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("openai_upload_file_error", status=exc.response.status_code, body=exc.response.text[:300])
            raise UpstreamError() from exc
        except httpx.TimeoutException as exc:
            logger.warning("openai_upload_file_timeout")
            raise GatewayTimeoutError() from exc

    async def get_file(self, file_id: str, *, api_key: str | None = None) -> dict:
        try:
            response = await self._client.get(
                f"/files/{file_id}",
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("openai_get_file_error", status=exc.response.status_code)
            raise UpstreamError() from exc
        except httpx.TimeoutException as exc:
            raise GatewayTimeoutError() from exc

    async def delete_file(self, file_id: str, *, api_key: str | None = None) -> dict:
        try:
            response = await self._client.delete(
                f"/files/{file_id}",
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("openai_delete_file_error", status=exc.response.status_code)
            raise UpstreamError() from exc
        except httpx.TimeoutException as exc:
            raise GatewayTimeoutError() from exc

    async def get_file_content(self, file_id: str, *, api_key: str | None = None) -> bytes:
        try:
            response = await self._client.get(
                f"/files/{file_id}/content",
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as exc:
            logger.warning("openai_get_file_content_error", status=exc.response.status_code)
            raise UpstreamError() from exc
        except httpx.TimeoutException as exc:
            raise GatewayTimeoutError() from exc

    async def create_batch(
        self,
        input_file_id: str,
        endpoint: str,
        completion_window: str,
        metadata: dict | None = None,
        *,
        api_key: str | None = None,
    ) -> dict:
        payload: dict = {
            "input_file_id": input_file_id,
            "endpoint": endpoint,
            "completion_window": completion_window,
        }
        if metadata:
            payload["metadata"] = metadata
        try:
            response = await self._client.post(
                "/batches",
                json=payload,
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("openai_create_batch_error", status=exc.response.status_code, body=exc.response.text[:300])
            raise UpstreamError() from exc
        except httpx.TimeoutException as exc:
            raise GatewayTimeoutError() from exc

    async def get_batch(self, batch_id: str, *, api_key: str | None = None) -> dict:
        try:
            response = await self._client.get(
                f"/batches/{batch_id}",
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("openai_get_batch_error", status=exc.response.status_code)
            raise UpstreamError() from exc
        except httpx.TimeoutException as exc:
            raise GatewayTimeoutError() from exc

    async def list_batches(
        self,
        after: str | None = None,
        limit: int = 20,
        *,
        api_key: str | None = None,
    ) -> dict:
        params: dict = {"limit": limit}
        if after:
            params["after"] = after
        try:
            response = await self._client.get(
                "/batches",
                params=params,
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("openai_list_batches_error", status=exc.response.status_code)
            raise UpstreamError() from exc
        except httpx.TimeoutException as exc:
            raise GatewayTimeoutError() from exc

    async def cancel_batch(self, batch_id: str, *, api_key: str | None = None) -> dict:
        try:
            response = await self._client.post(
                f"/batches/{batch_id}/cancel",
                headers=self._auth_headers(api_key),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("openai_cancel_batch_error", status=exc.response.status_code)
            raise UpstreamError() from exc
        except httpx.TimeoutException as exc:
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
        log = logger.bind(model=request.model, openai_model=payload["model"])

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
                "openai_direct_responses_http_error",
                status=exc.response.status_code,
                body=body,
            )
            raise UpstreamError() from exc

        except httpx.TimeoutException as exc:
            log.warning("openai_direct_responses_timeout")
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
        log = logger.bind(model=request.model, openai_model=payload["model"])

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
                        "openai_direct_responses_stream_error",
                        status=response.status_code,
                        body=body,
                    )
                    raise UpstreamError()

                log.debug("openai_direct_responses_stream_open")
                async for chunk in response.aiter_raw():
                    yield chunk

        except httpx.TimeoutException as exc:
            log.warning("openai_direct_responses_stream_timeout")
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

        # OpenAI API doesn't support input_type; exclude it
        payload = request.model_dump(exclude_none=True, exclude={"model", "provider", "input_type"})
        model_id = provider_model_id or request.model
        if not model_id:
            raise ValueError("Embeddings model must be resolved before adapter call")
        payload["model"] = _openai_model_id(model_id)
        if (label := _owner_user_label(owner)) is not None:
            payload.setdefault("user", label)
        log = logger.bind(model=request.model, openai_model=payload["model"])

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
            log.warning("openai_direct_embed_http_error", status=exc.response.status_code, body=body[:300])
            raise UpstreamError(upstream_detail=body) from exc

        except httpx.TimeoutException as exc:
            log.warning("openai_direct_embed_timeout")
            raise GatewayTimeoutError() from exc
