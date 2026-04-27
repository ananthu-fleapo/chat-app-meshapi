"""
Vertex AI provider adapter.

Two distinct API surfaces are used depending on the model publisher:

- **Google models** (``google/`` prefix) — native Gemini API:
    POST https://aiplatform.googleapis.com/v1/projects/{project}/locations/global
         /publishers/google/models/{model_id}:(generate|stream)GenerateContent
  Request/response use the Gemini ``contents`` / ``candidates`` schema.
  Streaming returns a JSON array of ``GenerateContentResponse`` objects.

- **Non-Google models** (e.g. Anthropic Claude) — OpenAI-compatible endpoint:
    POST https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}
         /locations/{location}/endpoints/openapi/chat/completions
  Request/response follow the OpenAI schema; SSE works out of the box.

Token lifecycle
--------------
- Tokens are valid for 60 minutes (Google default).
- We cache each token for 55 minutes to avoid expiry mid-request.
- Refresh is blocking (runs in a thread pool) so it doesn't block the event
  loop while making an outbound HTTP call to Google's token endpoint.

Model translation
-----------------
Clients use canonical RouterV model names (e.g. "google/gemini-2.5-pro").
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

def _is_google_model(vertex_model_id: str) -> bool:
    return vertex_model_id.startswith("google/")


def _gemini_url(project_id: str, vertex_model_id: str, *, stream: bool) -> str:
    """Build the native Gemini API URL for a google/ model."""
    action = "streamGenerateContent" if stream else "generateContent"
    return (
        f"https://aiplatform.googleapis.com/v1"
        f"/projects/{project_id}/locations/global"
        f"/publishers/google/models/{vertex_model_id}:{action}"
    )


def _to_gemini_payload(request: ChatCompletionRequest) -> dict:
    """Translate a ChatCompletionRequest into a Gemini generateContent payload."""
    system_parts: list[dict] = []
    contents: list[dict] = []

    for msg in request.messages:
        role = msg.role
        content = msg.content

        if role == "system":
            text = content if isinstance(content, str) else " ".join(
                p["text"] for p in content if isinstance(p, dict) and p.get("type") == "text"
            )
            system_parts.append({"text": text})
            continue

        gemini_role = "model" if role == "assistant" else "user"
        if isinstance(content, str):
            parts = [{"text": content}]
        elif isinstance(content, list):
            parts = [
                {"text": p["text"]}
                for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            ]
        else:
            parts = [{"text": str(content)}]

        contents.append({"role": gemini_role, "parts": parts})

    payload: dict = {"contents": contents}

    if system_parts:
        payload["systemInstruction"] = {"parts": system_parts}

    gen_config: dict = {}
    if request.temperature is not None:
        gen_config["temperature"] = request.temperature
    if request.max_tokens is not None:
        gen_config["maxOutputTokens"] = request.max_tokens
    if request.top_p is not None:
        gen_config["topP"] = request.top_p
    if request.stop is not None:
        gen_config["stopSequences"] = (
            request.stop if isinstance(request.stop, list) else [request.stop]
        )
    if gen_config:
        payload["generationConfig"] = gen_config

    return payload


def _gemini_usage(usage_meta: dict) -> dict:
    """Translate Gemini usageMetadata to OpenAI usage shape.

    thoughtsTokenCount (Gemini 2.5 thinking tokens) is billed output but not
    included in candidatesTokenCount, so we add it into completion_tokens and
    expose it via completion_tokens_details.reasoning_tokens (OpenAI o1/o3 convention).
    """
    prompt_tokens = usage_meta.get("promptTokenCount", 0)
    candidate_tokens = usage_meta.get("candidatesTokenCount", 0)
    thinking_tokens = usage_meta.get("thoughtsTokenCount", 0)

    result: dict = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": candidate_tokens + thinking_tokens,
        "total_tokens": usage_meta.get("totalTokenCount", 0),
    }
    if thinking_tokens:
        result["completion_tokens_details"] = {"reasoning_tokens": thinking_tokens}
    cached = usage_meta.get("cachedContentTokenCount", 0)
    if cached:
        result["prompt_tokens_details"] = {"cached_tokens": cached}
    return result


_FINISH_REASON_MAP: dict[str, str] = {
    "STOP": "stop",
    "MAX_TOKENS": "length",
    "SAFETY": "content_filter",
    "RECITATION": "content_filter",
    "OTHER": "stop",
}


def _from_gemini_response(body: dict, model: str) -> dict:
    """Convert a Gemini generateContent response to OpenAI chat completion shape."""
    candidates = body.get("candidates", [])
    usage = body.get("usageMetadata", {})
    choices = []
    for i, candidate in enumerate(candidates):
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        finish = _FINISH_REASON_MAP.get(candidate.get("finishReason", "STOP"), "stop")
        choices.append({
            "index": i,
            "message": {"role": "assistant", "content": text},
            "finish_reason": finish,
            "logprobs": None,
        })
    return {
        "id": f"chatcmpl-gemini-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": choices,
        "usage": _gemini_usage(usage),
    }


def _gemini_obj_to_sse_chunk(obj: dict, model: str, cid: str, created: int) -> bytes:
    """Convert one streamed Gemini GenerateContentResponse to an OpenAI SSE chunk."""
    candidates = obj.get("candidates", [])
    if not candidates:
        return b""

    candidate = candidates[0]
    parts = candidate.get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    finish_reason_raw = candidate.get("finishReason")
    finish_reason = _FINISH_REASON_MAP.get(finish_reason_raw, "stop") if finish_reason_raw else None

    delta: dict = {}
    if text:
        delta["content"] = text
    if not delta and finish_reason is None:
        return b""

    chunk: dict = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": delta,
            "finish_reason": finish_reason,
            "logprobs": None,
        }],
    }
    return b"data: " + json.dumps(chunk).encode() + b"\n\n"


async def _parse_gemini_stream(
    response: httpx.Response,
    model: str,
) -> AsyncGenerator[bytes, None]:
    """
    Consume a Gemini streamGenerateContent response and yield OpenAI SSE bytes.

    Vertex streams the body as a JSON array: ``[obj,\\nobj,\\n...]``.
    We use JSONDecoder.raw_decode() to peel off complete objects incrementally.

    Usage is emitted as a dedicated final chunk before [DONE] rather than
    per-content-chunk, because intermediate Gemini chunks report per-chunk
    candidatesTokenCount (not cumulative) while totalTokenCount is a running
    total — so the numbers only add up correctly on the final aggregated object.
    """
    cid = f"chatcmpl-gemini-{int(time.time())}"
    created = int(time.time())
    decoder = json.JSONDecoder()
    buffer = ""
    final_usage: dict | None = None

    async for text in response.aiter_text():
        buffer += text
        while True:
            # Strip leading whitespace, array brackets, and commas
            clean = buffer.lstrip(" \n\r\t,[")
            if not clean or clean == "]":
                buffer = ""
                break
            try:
                obj, idx = decoder.raw_decode(clean)
                buffer = clean[idx:]
            except json.JSONDecodeError:
                break  # wait for more data
            # Always overwrite — the last object in the stream has complete totals.
            if obj.get("usageMetadata"):
                final_usage = obj["usageMetadata"]
            chunk = _gemini_obj_to_sse_chunk(obj, model, cid, created)
            if chunk:
                yield chunk

    # Emit a usage-only chunk so _scan_sse_buf in inference.py captures accurate counts.
    if final_usage:
        usage_chunk: dict = {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [],
            "usage": _gemini_usage(final_usage),
        }
        yield b"data: " + json.dumps(usage_chunk).encode() + b"\n\n"

    yield b"data: [DONE]\n\n"


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

        # OpenAI-compatible endpoint — used for non-Google models (e.g. Anthropic)
        base_url = (
            f"https://{location}-aiplatform.googleapis.com/v1beta1"
            f"/projects/{project_id}/locations/{location}/endpoints/openapi"
        )
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout),
        )
        # Native Gemini endpoint — used for google/ models
        self._google_client = httpx.AsyncClient(
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
            await cls._instance._google_client.aclose()
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
        vertex_model = provider_model_id or request.model
        log = logger.bind(model=request.model, vertex_model=vertex_model)

        try:
            headers = await self._auth_headers()

            if _is_google_model(request.model):
                url = _gemini_url(self._project_id, vertex_model, stream=False)
                payload = _to_gemini_payload(request)
                response = await self._google_client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return _from_gemini_response(response.json(), vertex_model)

            payload = _build_payload(request, stream=False, owner=owner)
            payload["model"] = vertex_model
            response = await self._client.post("/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            log.error("vertex_http_error", status=exc.response.status_code, body=body, error=str(exc))
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
        vertex_model = provider_model_id or request.model
        log = logger.bind(model=request.model, vertex_model=vertex_model)

        try:
            headers = await self._auth_headers()

            if _is_google_model(request.model):
                url = _gemini_url(self._project_id, vertex_model, stream=True)
                payload = _to_gemini_payload(request)
                log.debug("vertex_gemini_stream_open")
                async with self._google_client.stream(
                    "POST", url, json=payload, headers=headers
                ) as response:
                    if response.status_code >= 400:
                        await response.aread()
                        body = response.text[:300]
                        log.warning("vertex_gemini_stream_error", status=response.status_code, body=body)
                        _classify_vertex_error(response.status_code, body)
                    async for chunk in _parse_gemini_stream(response, vertex_model):
                        yield chunk
                return

            payload = _build_payload(request, stream=True, owner=owner)
            payload["model"] = vertex_model
            # Vertex AI does not support stream_options (OpenRouter/OpenAI extension)
            payload.pop("stream_options", None)
            # Disable gzip — Vertex returns compressed SSE; aiter_raw() proxies raw bytes.
            headers["Accept-Encoding"] = "identity"
            log.debug("vertex_stream_open")
            async with self._client.stream(
                "POST", "/chat/completions", json=payload, headers=headers
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    body = response.text[:300]
                    log.warning("vertex_stream_error", status=response.status_code, body=body)
                    _classify_vertex_error(response.status_code, body)
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
        vertex_model = provider_model_id or request.model
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
                error=str(exc)
            )
            _classify_vertex_error(exc.response.status_code, body)

        except httpx.TimeoutException as exc:
            log.warning("vertex_embed_timeout")
            raise GatewayTimeoutError() from exc
