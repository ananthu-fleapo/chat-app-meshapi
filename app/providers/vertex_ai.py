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

from app.exceptions import GatewayTimeoutError, UnprocessableEntityError, UpstreamError
from app.providers.base import ProviderAdapter
from app.exceptions import _classify_vertex_error
from app.providers.openrouter import _build_payload
from app.schemas.chat import ChatCompletionRequest
from app.schemas.embeddings import EmbeddingsRequest

logger = structlog.get_logger()


# Canonical model name → Vertex AI model ID.
#
# Vertex AI's OpenAI-compatible endpoint (/endpoints/openapi/chat/completions)
# requires the model in "<publisher>/<model>" format for ALL models:
#   - Google models:    google/gemini-2.0-flash-001
#   - Anthropic models: anthropic/claude-3-5-sonnet@20241022
#
# The fallback in _vertex_model_id() prepends "google/" when no mapping exists
# and the canonical name doesn't already contain a slash, covering new Gemini
# previews that haven't been explicitly mapped yet.
_MODEL_MAP: dict[str, str] = {
    # ── Anthropic Claude on Vertex ────────────────────────────────────────────
    "anthropic/claude-3-5-sonnet": "anthropic/claude-3-5-sonnet@20241022",
    "anthropic/claude-3-5-sonnet-20241022": "anthropic/claude-3-5-sonnet@20241022",
    "anthropic/claude-3-5-haiku": "anthropic/claude-3-5-haiku@20241022",
    "anthropic/claude-3-5-haiku-20241022": "anthropic/claude-3-5-haiku@20241022",
    "anthropic/claude-3-opus": "anthropic/claude-3-opus@20240229",
    "anthropic/claude-3-opus-20240229": "anthropic/claude-3-opus@20240229",
    "anthropic/claude-3-sonnet": "anthropic/claude-3-sonnet@20240229",
    "anthropic/claude-3-haiku": "anthropic/claude-3-haiku@20240307",
    # ── Google Gemini 1.5 ─────────────────────────────────────────────────────
    "google/gemini-pro-1.5": "google/gemini-1.5-pro-002",
    "google/gemini-flash-1.5": "google/gemini-1.5-flash-002",
    # ── Google Gemini 2.0 ─────────────────────────────────────────────────────
    "google/gemini-2.0-flash": "google/gemini-2.0-flash-001",
    "google/gemini-2.0-flash-exp": "google/gemini-2.0-flash-exp",
    "google/gemini-2.0-flash-lite": "google/gemini-2.0-flash-lite-001",
    # ── Google Gemini 2.5 ─────────────────────────────────────────────────────
    "google/gemini-2.5-pro": "google/gemini-2.5-pro-preview-05-06",
    "google/gemini-2.5-flash": "google/gemini-2.5-flash-preview-04-17",
    # ── Google Gemini 3 ───────────────────────────────────────────────────────
    "google/gemini-3-flash-preview": "google/gemini-3-flash-preview",
    "gemini-3-flash-preview": "google/gemini-3-flash-preview",
    "google/gemini-3.1-pro-preview": "google/gemini-3.1-pro-preview",
    "gemini-3.1-pro-preview": "google/gemini-3.1-pro-preview",
}


def _vertex_model_id(canonical: str) -> str:
    """
    Translate a canonical RouterV model name to a Vertex AI model ID.

    Vertex's OpenAI-compatible endpoint requires '<publisher>/<model>' format.
    If the canonical name isn't in _MODEL_MAP and doesn't contain a '/', assume
    it's a Google model and prepend 'google/' so new previews work without
    explicit mapping.
    """
    if canonical in _MODEL_MAP:
        return _MODEL_MAP[canonical]
    # Already in publisher/model format (e.g. "google/gemini-2.5-pro-exp-03-25")
    if "/" in canonical:
        return canonical
    # Bare name — assume Google model
    return f"google/{canonical}"


# input_type → Vertex AI task_type
_TASK_TYPE_MAP: dict[str, str] = {
    "query": "RETRIEVAL_QUERY",
    "document": "RETRIEVAL_DOCUMENT",
    "classification": "CLASSIFICATION",
    "clustering": "CLUSTERING",
    "question_answering": "QUESTION_ANSWERING",
    "fact_verification": "FACT_VERIFICATION",
    "semantic_similarity": "SEMANTIC_SIMILARITY",
    "code_retrieval_query": "CODE_RETRIEVAL_QUERY",
}


def _build_vertex_embed_instances(
    request: EmbeddingsRequest,
) -> tuple[list[dict], dict]:
    """
    Translate EmbeddingsRequest into Vertex AI predict instances + parameters.

    Returns (instances, parameters). parameters may be empty.
    """
    inp = request.input
    task_type = _TASK_TYPE_MAP.get(request.input_type or "")
    parameters: dict = {}

    if isinstance(inp, list) and inp and isinstance(inp[0], int):
        raise UnprocessableEntityError(
            "Vertex AI text embeddings do not support token array inputs."
        )
    if isinstance(inp, list) and inp and isinstance(inp[0], list):
        raise UnprocessableEntityError(
            "Vertex AI text embeddings do not support token array inputs."
        )

    if isinstance(inp, str):
        raw = [inp]
    else:
        raw = inp  # type: ignore[assignment]

    instances = [{"content": t} for t in raw]
    if task_type:
        for inst in instances:
            inst["task_type"] = task_type
    if request.dimensions:
        parameters["outputDimensionality"] = request.dimensions

    return instances, parameters


def _vertex_embed_response_to_openai(body: dict, model: str | None = None) -> dict:
    """Convert Vertex AI predict response to OpenAI embeddings response shape."""
    predictions = body.get("predictions", [])
    data = []
    total_tokens = 0

    for i, pred in enumerate(predictions):
        embedding = pred["embeddings"]["values"]
        total_tokens += pred["embeddings"].get("statistics", {}).get("token_count", 0)
        data.append({"object": "embedding", "index": i, "embedding": embedding})

    result: dict = {
        "object": "list",
        "data": data,
        "usage": {"prompt_tokens": total_tokens, "total_tokens": total_tokens},
    }
    if model:
        result["model"] = model
    return result


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
        self._project_id = project_id
        self._location = location

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
        payload["model"] = _vertex_model_id(provider_model_id or payload["model"])
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
            _classify_vertex_error(exc.response.status_code, body)

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
        payload["model"] = _vertex_model_id(provider_model_id or payload["model"])
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
                    log.warning(
                        "vertex_stream_error", status=response.status_code, body=body
                    )
                    _classify_vertex_error(response.status_code, body)

                log.debug("vertex_stream_open")
                async for chunk in response.aiter_raw():
                    yield chunk

        except httpx.TimeoutException as exc:
            log.warning("vertex_stream_timeout")
            raise GatewayTimeoutError() from exc

    def _build_vertex_embed_predict_url(self, vertex_model_id: str) -> str:
        """Build the :predict URL for Vertex AI embeddings."""
        model_segment = vertex_model_id.split("/")[-1]
        return (
            f"https://{self._location}-aiplatform.googleapis.com/v1"
            f"/projects/{self._project_id}/locations/{self._location}"
            f"/publishers/google/models/{model_segment}:predict"
        )

    async def embeddings(
        self,
        request: EmbeddingsRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        vertex_model = _vertex_model_id(provider_model_id or request.model)
        log = logger.bind(model=request.model, vertex_model=vertex_model)

        instances, parameters = _build_vertex_embed_instances(request)

        url = self._build_vertex_embed_predict_url(vertex_model)
        payload: dict = {"instances": instances}
        if parameters:
            payload["parameters"] = parameters

        try:
            headers = await self._auth_headers()
            response = await self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return _vertex_embed_response_to_openai(response.json(), model=vertex_model)

        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            log.warning(
                "vertex_embed_http_error",
                status=exc.response.status_code,
                body=body[:300],
            )
            _classify_vertex_error(exc.response.status_code, body)

        except httpx.TimeoutException as exc:
            log.warning("vertex_embed_timeout")
            raise GatewayTimeoutError() from exc
