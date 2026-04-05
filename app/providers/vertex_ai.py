"""
Vertex AI provider adapter.

Vertex AI exposes an OpenAI-compatible REST endpoint, so the HTTP layer is
nearly identical to OpenRouterAdapter.  The key difference is authentication:
instead of a static API key, we use a short-lived Google OAuth2 Bearer token
derived from a service account JSON credential.

Token lifecycle
--------------
- Tokens are valid for 60 minutes (Google default).
- We cache each token for 55 minutes to avoid expiry mid-request.
- Refresh is blocking (runs in a thread pool) so it doesn't block the event
  loop while making an outbound HTTP call to Google's token endpoint.

Endpoint
--------
https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project_id}
    /locations/{location}/endpoints/openapi

Model translation
-----------------
Clients use canonical RouterV model names (e.g. "anthropic/claude-3-5-sonnet").
This adapter translates them to Vertex AI model IDs before forwarding.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator

import httpx
import structlog

from app.exceptions import GatewayTimeoutError, UpstreamError
from app.providers.base import ProviderAdapter
from app.providers.openrouter import _build_payload
from app.schemas.chat import ChatCompletionRequest

logger = structlog.get_logger()

# Canonical model name → Vertex AI model ID
_MODEL_MAP: dict[str, str] = {
    "anthropic/claude-3-5-sonnet":          "claude-3-5-sonnet@20241022",
    "anthropic/claude-3-5-sonnet-20241022": "claude-3-5-sonnet@20241022",
    "anthropic/claude-3-5-haiku":           "claude-3-5-haiku@20241022",
    "anthropic/claude-3-5-haiku-20241022":  "claude-3-5-haiku@20241022",
    "anthropic/claude-3-opus":              "claude-3-opus@20240229",
    "anthropic/claude-3-opus-20240229":     "claude-3-opus@20240229",
    "anthropic/claude-3-sonnet":            "claude-3-sonnet@20240229",
    "anthropic/claude-3-haiku":             "claude-3-haiku@20240307",
    "google/gemini-pro-1.5":               "gemini-1.5-pro-002",
    "google/gemini-flash-1.5":             "gemini-1.5-flash-002",
    "google/gemini-2.0-flash":             "gemini-2.0-flash-001",
    "google/gemini-2.0-flash-exp":         "gemini-2.0-flash-exp",
    "google/gemini-2.5-pro":               "gemini-2.5-pro-preview-03-25",
}


def _vertex_model_id(canonical: str) -> str:
    """Translate a canonical RouterV model name to a Vertex AI model ID."""
    return _MODEL_MAP.get(canonical, canonical)


def _refresh_token_sync(service_account_json: str) -> tuple[str, float]:
    """
    Synchronous token refresh — called inside a thread pool so it doesn't
    block the event loop.  Returns (token, expiry_epoch_seconds).
    """
    from google.auth.transport.requests import Request as GoogleRequest  # type: ignore[import]
    from google.oauth2 import service_account  # type: ignore[import]

    creds = service_account.Credentials.from_service_account_info(
        json.loads(service_account_json),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(GoogleRequest())
    expiry = time.time() + 55 * 60  # 55-min cache (tokens last 60 min)
    return creds.token, expiry


class VertexAIAdapter(ProviderAdapter):
    """Singleton adapter for Vertex AI's OpenAI-compatible chat endpoint."""

    _instance: "VertexAIAdapter | None" = None

    def __init__(
        self,
        project_id: str,
        location: str,
        service_account_json: str,
        timeout: float,
    ) -> None:
        self._service_account_json = service_account_json
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

        base_url = (
            f"https://{location}-aiplatform.googleapis.com/v1beta1"
            f"/projects/{project_id}/locations/{location}/endpoints/openapi"
        )
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout),
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @classmethod
    def init(
        cls,
        project_id: str,
        location: str,
        service_account_json: str,
        timeout: float = 120.0,
    ) -> "VertexAIAdapter":
        cls._instance = cls(
            project_id=project_id,
            location=location,
            service_account_json=service_account_json,
            timeout=timeout,
        )
        logger.info(
            "vertex_ai_adapter_ready",
            project_id=project_id,
            location=location,
        )
        return cls._instance

    @classmethod
    def get(cls) -> "VertexAIAdapter":
        if cls._instance is None:
            raise RuntimeError(
                "VertexAIAdapter not initialized. Call VertexAIAdapter.init() in lifespan."
            )
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        if cls._instance is not None:
            await cls._instance._client.aclose()
            cls._instance = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def _auth_headers(self) -> dict[str, str]:
        """
        Return Authorization header with a valid Google OAuth2 Bearer token.
        Refreshes the token in a thread pool when it has expired.
        """
        now = time.time()
        if not self._access_token or now >= self._token_expiry:
            token, expiry = await asyncio.to_thread(
                _refresh_token_sync, self._service_account_json
            )
            self._access_token = token
            self._token_expiry = expiry
            logger.debug("vertex_ai_token_refreshed")
        return {"Authorization": f"Bearer {self._access_token}"}

    # ── ProviderAdapter interface ─────────────────────────────────────────────

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        payload = _build_payload(request, stream=False, owner=owner)
        payload["model"] = provider_model_id or _vertex_model_id(payload["model"])
        log = logger.bind(model=request.model, vertex_model=payload["model"])

        try:
            headers = await self._auth_headers()
            response = await self._client.post(
                "/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            log.warning("vertex_http_error", status=exc.response.status_code, body=body)
            raise UpstreamError() from exc

        except httpx.TimeoutException as exc:
            log.warning("vertex_timeout")
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
        payload["model"] = provider_model_id or _vertex_model_id(payload["model"])
        log = logger.bind(model=request.model, vertex_model=payload["model"])

        try:
            headers = await self._auth_headers()
            async with self._client.stream(
                "POST",
                "/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    body = response.text[:300]
                    log.warning("vertex_stream_error", status=response.status_code, body=body)
                    raise UpstreamError()

                log.debug("vertex_stream_open")
                async for chunk in response.aiter_raw():
                    yield chunk

        except httpx.TimeoutException as exc:
            log.warning("vertex_stream_timeout")
            raise GatewayTimeoutError() from exc
