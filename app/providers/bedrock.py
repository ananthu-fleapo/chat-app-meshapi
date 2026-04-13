"""
AWS Bedrock provider adapter.

Uses the Bedrock Converse API — a unified interface across all Bedrock models.
Auth is handled by aiobotocore (async boto3) using SigV4 signing.

Protocol differences from OpenAI
----------------------------------
Bedrock Converse is NOT an OpenAI-compatible API, so this adapter must:
  1. Convert OpenAI-style messages to Bedrock Converse format.
  2. Map canonical RouterV model names to Bedrock model IDs.
  3. Convert Bedrock responses back to OpenAI format.
  4. Convert Bedrock streaming events back to OpenAI SSE bytes.

Converse request shape
-----------------------
{
    "modelId": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "messages": [{"role": "user", "content": [{"text": "..."}]}],
    "system": [{"text": "system prompt text"}],   # optional
    "inferenceConfig": {"maxTokens": 4096, "temperature": 0.7, "topP": 0.9}
}

Converse response shape
------------------------
{
    "output": {"message": {"role": "assistant", "content": [{"text": "..."}]}},
    "usage": {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
    "stopReason": "end_turn"
}

Streaming events (converse_stream)
------------------------------------
messageStart        → role begins
contentBlockStart   → new content block
contentBlockDelta   → text delta {"delta": {"text": "..."}}
contentBlockStop    → end of block
messageStop         → end_turn / stop reason
metadata            → usage statistics
"""

from __future__ import annotations

import json
import struct
import uuid
from collections.abc import AsyncGenerator

import httpx
import structlog

from app.exceptions import GatewayTimeoutError, UpstreamError
from app.providers.base import ProviderAdapter
from app.schemas.chat import ChatCompletionRequest
from app.schemas.responses import RESPONSES_ONLY_FIELDS, ResponsesRequest
from app.schemas.embeddings import EmbeddingsRequest

logger = structlog.get_logger()

# Canonical model name → AWS Bedrock cross-region inference profile ID.
# Fallback used when provider_model_id is not set in the DB.
# All active models use the us. geo cross-region prefix (routes across us-east-1/us-west-2).
# Confirmed live as of 2026-04 via test_bedrock_models.py.
_MODEL_MAP: dict[str, str] = {
    # ── Claude 4.x ────────────────────────────────────────────────────────────
    "anthropic/claude-sonnet-4-5":        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "anthropic/claude-opus-4-5":          "us.anthropic.claude-opus-4-5-20251101-v1:0",
    "anthropic/claude-sonnet-4":          "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "anthropic/claude-opus-4-1":          "us.anthropic.claude-opus-4-1-20250805-v1:0",
    "anthropic/claude-haiku-4-5":         "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    # ── Claude 3.x (only haiku still active; 3-5 sonnet/haiku and 3-7 are legacy) ──
    "anthropic/claude-3-haiku":           "us.anthropic.claude-3-haiku-20240307-v1:0",
    # ── Amazon Nova ───────────────────────────────────────────────────────────
    "amazon/nova-lite-v1":                "us.amazon.nova-lite-v1:0",
    "amazon/nova-micro-v1":               "us.amazon.nova-micro-v1:0",
    "amazon/nova-pro-v1":                 "us.amazon.nova-pro-v1:0",
    # ── Amazon Titan Embed ────────────────────────────────────────────────────
    "amazon/titan-embed-text-v2":          "amazon.titan-embed-text-v2:0",
    "amazon/titan-embed-text-v1":          "amazon.titan-embed-text-v1:2",
    # ── Cohere Embed ──────────────────────────────────────────────────────────
    "cohere/embed-english-v3":             "cohere.embed-english-v3",
    "cohere/embed-multilingual-v3":        "cohere.embed-multilingual-v3",
}


def _bedrock_model_id(canonical: str) -> str:
    """Translate a canonical RouterV model name to a Bedrock model ID."""
    return _MODEL_MAP.get(canonical, canonical)


# ── Message format conversion ─────────────────────────────────────────────────

def _content_to_bedrock(content: str | list) -> list[dict]:
    """
    Convert OpenAI message content to Bedrock Converse content blocks.

    OpenAI content can be:
      - str: plain text
      - list of {"type": "text", "text": "..."} parts

    Bedrock content blocks:
      - [{"text": "..."}]
    """
    if isinstance(content, str):
        return [{"text": content}]

    blocks: list[dict] = []
    for part in content:
        if isinstance(part, dict):
            if part.get("type") == "text":
                blocks.append({"text": part.get("text", "")})
            # Image parts could be added here in the future
    return blocks or [{"text": ""}]


def _messages_to_bedrock(
    messages: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    Split OpenAI messages into (bedrock_messages, system_blocks).

    - system messages are extracted into the top-level "system" field.
    - user/assistant messages are converted to Bedrock Converse format.

    Returns:
        bedrock_messages: list of {"role": ..., "content": [...]} dicts
        system_blocks: list of {"text": "..."} dicts (may be empty)
    """
    system_parts: list[str] = []
    bedrock_msgs: list[dict] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            # Accumulate all system messages into one
            if isinstance(content, str):
                system_parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        system_parts.append(part.get("text", ""))
        else:
            # Bedrock uses "user" and "assistant" — no other roles supported
            bedrock_role = "assistant" if role == "assistant" else "user"
            bedrock_msgs.append({
                "role": bedrock_role,
                "content": _content_to_bedrock(content),
            })

    system_blocks = [{"text": "\n".join(system_parts)}] if system_parts else []
    return bedrock_msgs, system_blocks


def _build_bedrock_body(request: ChatCompletionRequest) -> dict:
    """
    Build the Bedrock Converse request body (without modelId).

    Used for both the HTTP/Bearer path (modelId goes in the URL) and the
    aiobotocore/SigV4 path (modelId passed as a separate kwarg).
    """
    messages_raw = [m.model_dump() for m in request.messages]
    bedrock_messages, system_blocks = _messages_to_bedrock(messages_raw)

    inference_config: dict = {}
    if request.max_tokens is not None:
        inference_config["maxTokens"] = request.max_tokens
    if request.temperature is not None:
        inference_config["temperature"] = request.temperature
    if request.top_p is not None:
        inference_config["topP"] = request.top_p

    body: dict = {"messages": bedrock_messages}
    if system_blocks:
        body["system"] = system_blocks
    if inference_config:
        body["inferenceConfig"] = inference_config

    return body


def _build_bedrock_request(request: ChatCompletionRequest, model_id: str) -> dict:
    """Build full Bedrock Converse kwargs dict (with modelId) for aiobotocore."""
    return {"modelId": model_id, **_build_bedrock_body(request)}


def _build_responses_payload(
    request: ResponsesRequest,
    *,
    stream: bool,
    provider_model_id: str | None = None,
) -> dict:
    """
    Build the payload for the Bedrock mantle /responses endpoint.

    The bedrock-mantle endpoint is OpenAI-compatible so the payload mirrors the
    OpenAI Responses API format.  RouterV-only fields (template, variables,
    session_id) are stripped; model is translated via _bedrock_model_id if no
    explicit provider_model_id is supplied.
    """
    payload = request.model_dump(exclude_none=True, exclude=RESPONSES_ONLY_FIELDS)
    payload["stream"] = stream
    payload["model"] = provider_model_id or _bedrock_model_id(request.model or "")
    return payload


# ── AWS EventStream binary parser ─────────────────────────────────────────────

def _parse_eventstream_frames(buf: bytes) -> tuple[list[dict], bytes]:
    """
    Parse complete AWS EventStream frames from a byte buffer.

    Each Bedrock streaming event is framed as:
      [4B total_len][4B headers_len][4B prelude_crc]
      [headers_bytes][payload_bytes][4B message_crc]

    Header value type 7 = UTF-8 string (the only type Bedrock emits).

    Returns (events, remaining_bytes) where remaining_bytes is any partial
    frame that needs more data before it can be parsed.

    Each event dict has the shape Bedrock uses, e.g.:
      {"contentBlockDelta": {"delta": {"text": "..."}, "contentBlockIndex": 0}}
      {"messageStop": {"stopReason": "end_turn"}}
      {"metadata": {"usage": {"inputTokens": 10, "outputTokens": 5}}}
    """
    events: list[dict] = []

    while len(buf) >= 16:  # minimum valid frame: 12 prelude + 4 msg_crc
        total_len = struct.unpack(">I", buf[:4])[0]
        if len(buf) < total_len:
            break  # incomplete frame — wait for more data

        frame = buf[:total_len]
        buf = buf[total_len:]

        headers_len = struct.unpack(">I", frame[4:8])[0]
        # frame[8:12] = prelude CRC — skip verification

        # Parse headers to find :event-type
        pos = 12
        headers_end = 12 + headers_len
        event_type = ""
        while pos < headers_end:
            name_len = frame[pos]; pos += 1
            name = frame[pos:pos + name_len].decode(); pos += name_len
            vtype = frame[pos]; pos += 1
            if vtype == 7:  # string
                vlen = struct.unpack(">H", frame[pos:pos + 2])[0]; pos += 2
                val = frame[pos:pos + vlen].decode(); pos += vlen
                if name == ":event-type":
                    event_type = val
            # Non-string types don't appear in Bedrock stream headers — skip

        if not event_type:
            continue

        payload_bytes = frame[headers_end:total_len - 4]  # -4 = message CRC
        try:
            payload = json.loads(payload_bytes) if payload_bytes else {}
        except json.JSONDecodeError:
            continue

        events.append({event_type: payload})

    return events, buf


# ── Response format conversion ────────────────────────────────────────────────

def _normalize_responses_usage(body: dict) -> None:
    """
    Normalize OpenAI-style usage field names in a Responses API response body.

    The bedrock-mantle endpoint returns OpenAI field names (input_tokens /
    output_tokens).  RouterV usage logging expects prompt_tokens /
    completion_tokens.  Mutates body in-place.
    """
    usage = body.get("usage")
    if not usage:
        return
    if "input_tokens" in usage and "prompt_tokens" not in usage:
        usage["prompt_tokens"] = usage.pop("input_tokens")
    if "output_tokens" in usage and "completion_tokens" not in usage:
        usage["completion_tokens"] = usage.pop("output_tokens")
    if "input_tokens_details" in usage and "prompt_tokens_details" not in usage:
        usage["prompt_tokens_details"] = usage.pop("input_tokens_details")


def _bedrock_response_to_openai(bedrock_resp: dict, canonical_model: str) -> dict:
    """Convert a Bedrock Converse response to OpenAI chat.completion format."""
    message = bedrock_resp.get("output", {}).get("message", {})
    content_blocks = message.get("content", [])
    text = "".join(block.get("text", "") for block in content_blocks)

    usage = bedrock_resp.get("usage", {})
    stop_reason = bedrock_resp.get("stopReason", "end_turn")

    # Map Bedrock stop reasons to OpenAI finish_reason
    finish_reason_map = {
        "end_turn": "stop",
        "max_tokens": "length",
        "stop_sequence": "stop",
        "tool_use": "tool_calls",
        "guardrail_intervened": "content_filter",
    }
    finish_reason = finish_reason_map.get(stop_reason, "stop")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:20]}",
        "object": "chat.completion",
        "model": canonical_model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": usage.get("inputTokens", 0),
            "completion_tokens": usage.get("outputTokens", 0),
            "total_tokens": usage.get("totalTokens", 0),
        },
    }


def _bedrock_stream_events_to_sse(
    events: list[dict],
    completion_id: str,
    canonical_model: str,
) -> bytes:
    """
    Convert a batch of Bedrock streaming events to OpenAI SSE bytes.
    Returns empty bytes if no yielable content in this batch.
    """
    chunks: list[bytes] = []

    for event in events:
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            text = delta.get("text", "")
            if text:
                payload = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "model": canonical_model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": text},
                            "finish_reason": None,
                        }
                    ],
                }
                chunks.append(f"data: {json.dumps(payload)}\n\n".encode())

        elif "messageStop" in event:
            stop_reason = event["messageStop"].get("stopReason", "end_turn")
            finish_reason_map = {
                "end_turn": "stop",
                "max_tokens": "length",
                "stop_sequence": "stop",
            }
            finish_reason = finish_reason_map.get(stop_reason, "stop")
            payload = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "model": canonical_model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": finish_reason,
                    }
                ],
            }
            chunks.append(f"data: {json.dumps(payload)}\n\n".encode())

        elif "metadata" in event:
            # Emit a usage chunk (mirrors OpenRouter's stream_options.include_usage)
            usage = event["metadata"].get("usage", {})
            if usage:
                prompt_tokens = usage.get("inputTokens", 0)
                completion_tokens = usage.get("outputTokens", 0)
                payload = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "model": canonical_model,
                    "choices": [],
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                    },
                }
                chunks.append(f"data: {json.dumps(payload)}\n\n".encode())

    return b"".join(chunks)


def _build_bedrock_embed_body(request: "EmbeddingsRequest", model_id: str) -> dict:
    """
    Build the InvokeModel request body for Bedrock embedding models.

    - Amazon Titan Text (titan-embed-text-*): accepts a single string.
    - Cohere Embed: accepts a list of strings.

    Token-array inputs (list[int] / list[list[int]]) are not supported and
    raise UpstreamError immediately.
    """
    raw_input = request.input

    # Reject token arrays
    if isinstance(raw_input, list) and raw_input and isinstance(raw_input[0], int):
        raise UpstreamError(upstream_detail="Bedrock embedding models do not accept pre-tokenised (integer) inputs.")
    if isinstance(raw_input, list) and raw_input and isinstance(raw_input[0], list):
        raise UpstreamError(upstream_detail="Bedrock embedding models do not accept pre-tokenised (integer) inputs.")

    # ── Titan Text ────────────────────────────────────────────────────────────
    if model_id.startswith("amazon.titan-embed"):
        if isinstance(raw_input, list) and len(raw_input) > 1:
            raise UpstreamError(
                upstream_detail="Amazon Titan Embed does not support batched inputs. Send one string at a time."
            )
        text = raw_input if isinstance(raw_input, str) else (raw_input[0] if raw_input else "")
        body = {"inputText": text}
        if request.dimensions is not None:
            body["dimensions"] = request.dimensions
        return body

    # ── Cohere Embed ──────────────────────────────────────────────────────────
    if model_id.startswith("cohere.embed"):
        texts = [raw_input] if isinstance(raw_input, str) else list(raw_input)
        _input_type_map = {
            "query": "search_query",
            "document": "search_document",
            "classification": "classification",
            "clustering": "clustering",
        }
        cohere_input_type = _input_type_map.get(request.input_type or "", "search_document")
        body = {"texts": texts, "input_type": cohere_input_type}
        if request.encoding_format == "float":
            body["embedding_types"] = ["float"]
        return body

    raise UpstreamError(upstream_detail=f"Unsupported Bedrock embedding model: {model_id}")


def _bedrock_embed_response_to_openai(response_body: dict, model_id: str, canonical_model: str) -> dict:
    """Convert a Bedrock InvokeModel embedding response to OpenAI list format."""
    if model_id.startswith("amazon.titan-embed"):
        embeddings = [response_body["embedding"]]
        token_count = response_body.get("inputTextTokenCount", 0)
    elif model_id.startswith("cohere.embed"):
        raw = response_body.get("embeddings", [])
        # When embedding_types was requested, Cohere returns {"float": [[...]]}
        embeddings = raw.get("float", []) if isinstance(raw, dict) else raw
        token_count = 0  # Cohere InvokeModel does not return token counts
    else:
        embeddings = []
        token_count = 0

    return {
        "object": "list",
        "data": [
            {"object": "embedding", "index": i, "embedding": emb}
            for i, emb in enumerate(embeddings)
        ],
        "model": canonical_model,
        "usage": {"prompt_tokens": token_count, "total_tokens": token_count},
    }


# ── Adapter ───────────────────────────────────────────────────────────────────

class BedrockAdapter(ProviderAdapter):
    """
    Singleton adapter for AWS Bedrock Converse API.

    Two auth modes:
      Bearer token  — api_key set → httpx + Authorization: Bearer header.
                      Uses _parse_eventstream_frames for streaming.
      SigV4 / IAM   — aws_access_key_id + aws_secret_access_key set →
                      aiobotocore handles signing and eventstream decoding.

    Bearer takes priority when both are configured.
    """

    _instance: "BedrockAdapter | None" = None

    def __init__(
        self,
        region: str,
        timeout: float,
        api_key: str = "",
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
    ) -> None:
        self._region = region
        self._timeout = timeout
        self._api_key = api_key
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        # Shared httpx client for bearer-token path (connection-pooled).
        # Always initialized so per-request bearer keys work even when no
        # system api_key is configured.
        self._http_client: httpx.AsyncClient = httpx.AsyncClient(timeout=timeout)
        # Dedicated client for the bedrock-mantle OpenAI-compatible endpoint.
        # Always initialized — used for both bearer and SigV4 auth on /responses.
        self._mantle_client = httpx.AsyncClient(timeout=timeout)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @classmethod
    def init(
        cls,
        region: str,
        timeout: float = 120.0,
        api_key: str = "",
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
    ) -> "BedrockAdapter":
        cls._instance = cls(
            region=region,
            timeout=timeout,
            api_key=api_key,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        auth_mode = "bearer" if api_key else "sigv4"
        logger.info("bedrock_adapter_ready", region=region, auth=auth_mode)
        return cls._instance

    @classmethod
    def get(cls) -> "BedrockAdapter":
        if cls._instance is None:
            raise RuntimeError(
                "BedrockAdapter not initialized. Call BedrockAdapter.init() in lifespan."
            )
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        if cls._instance:
            if cls._instance._http_client:
                await cls._instance._http_client.aclose()
            await cls._instance._mantle_client.aclose()
        cls._instance = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _bearer_key(self, api_key: str | None) -> str:
        """Return the effective bearer key for this request (per-owner > system)."""
        return api_key or self._api_key

    def _use_bearer(self, api_key: str | None) -> bool:
        return bool(self._bearer_key(api_key))

    def _runtime_url(self, path: str) -> str:
        return f"https://bedrock-runtime.{self._region}.amazonaws.com{path}"

    def _bearer_headers(self, key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _make_sigv4_session(self):
        """Create an aiobotocore session configured with IAM credentials."""
        import aiobotocore.session  # type: ignore[import]

        session = aiobotocore.session.get_session()
        return session.create_client(
            "bedrock-runtime",
            region_name=self._region,
            aws_access_key_id=self._aws_access_key_id,
            aws_secret_access_key=self._aws_secret_access_key,
        )

    def _mantle_url(self, path: str) -> str:
        return f"https://bedrock-mantle.{self._region}.api.aws/v1{path}"

    def _sign_sigv4_headers(self, method: str, url: str, body_bytes: bytes) -> dict[str, str]:
        """Sign an arbitrary HTTP request with SigV4 for the bedrock service."""
        from botocore.auth import SigV4Auth  # type: ignore[import]
        from botocore.awsrequest import AWSRequest  # type: ignore[import]
        from botocore.credentials import Credentials  # type: ignore[import]

        creds = Credentials(self._aws_access_key_id, self._aws_secret_access_key)
        req = AWSRequest(method=method, url=url, data=body_bytes)
        req.headers["Content-Type"] = "application/json"
        SigV4Auth(creds, "bedrock-mantle", self._region).add_auth(req)
        return dict(req.headers)

    # ── ProviderAdapter interface ─────────────────────────────────────────────

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        bedrock_model = provider_model_id or _bedrock_model_id(request.model)
        log = logger.bind(model=request.model, bedrock_model=bedrock_model)

        try:
            if self._use_bearer(api_key):
                return await self._converse_http(request, bedrock_model, api_key, log)
            else:
                return await self._converse_sigv4(request, bedrock_model, log)
        except (GatewayTimeoutError, UpstreamError):
            raise
        except Exception as exc:
            err_name = type(exc).__name__
            if "Timeout" in err_name or "timeout" in str(exc).lower():
                log.warning("bedrock_timeout")
                raise GatewayTimeoutError() from exc
            log.warning("bedrock_error", error=str(exc))
            raise UpstreamError() from exc

    async def stream_chat_completion(
        self,
        request: ChatCompletionRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        bedrock_model = provider_model_id or _bedrock_model_id(request.model)
        log = logger.bind(model=request.model, bedrock_model=bedrock_model)
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:20]}"

        role_payload = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "model": request.model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(role_payload)}\n\n".encode()

        try:
            if self._use_bearer(api_key):
                async for chunk in self._converse_stream_http(
                    request, bedrock_model, api_key, log, completion_id
                ):
                    yield chunk
            else:
                async for chunk in self._converse_stream_sigv4(
                    request, bedrock_model, log, completion_id
                ):
                    yield chunk
        except (GatewayTimeoutError, UpstreamError):
            raise
        except Exception as exc:
            err_name = type(exc).__name__
            if "Timeout" in err_name or "timeout" in str(exc).lower():
                log.warning("bedrock_stream_timeout")
                raise GatewayTimeoutError() from exc
            log.warning("bedrock_stream_error", error=str(exc))
            raise UpstreamError(upstream_detail=str(exc)) from exc

        yield b"data: [DONE]\n\n"

    async def embeddings(
        self,
        request: "EmbeddingsRequest",
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        bedrock_model = provider_model_id or _bedrock_model_id(request.model)
        log = logger.bind(model=request.model, bedrock_model=bedrock_model)

        try:
            body = _build_bedrock_embed_body(request, bedrock_model)
            if self._use_bearer(api_key):
                return await self._embed_http(request.model, bedrock_model, body, api_key, log)
            else:
                return await self._embed_sigv4(request.model, bedrock_model, body, log)
        except (GatewayTimeoutError, UpstreamError):
            raise
        except Exception as exc:
            err_name = type(exc).__name__
            if "Timeout" in err_name or "timeout" in str(exc).lower():
                log.warning("bedrock_embed_timeout")
                raise GatewayTimeoutError() from exc
            log.warning("bedrock_embed_error", error=str(exc))
            raise UpstreamError(upstream_detail=str(exc)) from exc

    async def _embed_http(
        self, canonical_model: str, bedrock_model: str, body: dict, api_key: str | None, log
    ) -> dict:
        key = self._bearer_key(api_key)
        url = self._runtime_url(f"/model/{bedrock_model}/invoke")
        resp = await self._http_client.post(
            url,
            content=json.dumps(body),
            headers={**self._bearer_headers(key), "Accept": "application/json"},
        )
        if resp.status_code != 200:
            log.warning("bedrock_embed_http_error", status=resp.status_code, body=resp.text[:200])
            raise UpstreamError(upstream_detail=resp.text)
        return _bedrock_embed_response_to_openai(resp.json(), bedrock_model, canonical_model)

    async def _embed_sigv4(
        self, canonical_model: str, bedrock_model: str, body: dict, log
    ) -> dict:
        async with self._make_sigv4_session() as client:
            response = await client.invoke_model(
                modelId=bedrock_model,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            response_body = json.loads(await response["body"].read())
        return _bedrock_embed_response_to_openai(response_body, bedrock_model, canonical_model)

    # ── Bearer / httpx path ───────────────────────────────────────────────────

    async def _converse_http(self, request, bedrock_model, api_key, log) -> dict:
        key = self._bearer_key(api_key)
        url = self._runtime_url(f"/model/{bedrock_model}/converse")
        body = _build_bedrock_body(request)
        resp = await self._http_client.post(
            url, json=body, headers=self._bearer_headers(key)
        )
        if resp.status_code != 200:
            log.warning("bedrock_http_error", status=resp.status_code, body=resp.text[:200])
            raise UpstreamError()
        return _bedrock_response_to_openai(resp.json(), request.model)

    async def _converse_stream_http(
        self, request, bedrock_model, api_key, log, completion_id
    ) -> AsyncGenerator[bytes, None]:
        key = self._bearer_key(api_key)
        url = self._runtime_url(f"/model/{bedrock_model}/converse-stream")
        body = _build_bedrock_body(request)

        log.debug("bedrock_stream_open", auth="bearer")
        async with self._http_client.stream(
            "POST", url, json=body, headers=self._bearer_headers(key)
        ) as resp:
            if resp.status_code != 200:
                await resp.aread()
                log.warning("bedrock_stream_http_error", status=resp.status_code)
                raise UpstreamError()

            buf = b""
            async for raw_chunk in resp.aiter_raw():
                buf += raw_chunk
                events, buf = _parse_eventstream_frames(buf)
                if events:
                    sse = _bedrock_stream_events_to_sse(events, completion_id, request.model)
                    if sse:
                        yield sse

    # ── SigV4 / aiobotocore path ──────────────────────────────────────────────

    async def _converse_sigv4(self, request, bedrock_model, log) -> dict:
        kwargs = _build_bedrock_request(request, bedrock_model)
        async with self._make_sigv4_session() as client:
            response = await client.converse(**kwargs)
        return _bedrock_response_to_openai(response, request.model)

    async def _converse_stream_sigv4(
        self, request, bedrock_model, log, completion_id
    ) -> AsyncGenerator[bytes, None]:
        kwargs = _build_bedrock_request(request, bedrock_model)
        log.debug("bedrock_stream_open", auth="sigv4")
        async with self._make_sigv4_session() as client:
            response = await client.converse_stream(**kwargs)
            stream = response.get("stream")
            if stream is None:
                raise UpstreamError()
            async for event in stream:
                sse_bytes = _bedrock_stream_events_to_sse([event], completion_id, request.model)
                if sse_bytes:
                    yield sse_bytes

    # ── Responses API — bearer path ───────────────────────────────────────────

    async def _responses_http(
        self, request: ResponsesRequest, bedrock_model: str, api_key: str | None, log
    ) -> dict:
        key = self._bearer_key(api_key)
        url = self._mantle_url("/responses")
        payload = _build_responses_payload(request, stream=False, provider_model_id=bedrock_model)
        resp = await self._mantle_client.post(
            url, json=payload, headers=self._bearer_headers(key)
        )
        if resp.status_code != 200:
            log.warning("bedrock_responses_http_error", status=resp.status_code, body=resp.text[:200])
            raise UpstreamError()
        body = resp.json()
        _normalize_responses_usage(body)
        return body

    async def _responses_stream_http(
        self, request: ResponsesRequest, bedrock_model: str, api_key: str | None, log
    ) -> AsyncGenerator[bytes, None]:
        key = self._bearer_key(api_key)
        url = self._mantle_url("/responses")
        payload = _build_responses_payload(request, stream=True, provider_model_id=bedrock_model)
        log.debug("bedrock_responses_stream_open", auth="bearer")
        async with self._mantle_client.stream(
            "POST", url, json=payload, headers=self._bearer_headers(key)
        ) as resp:
            if resp.status_code != 200:
                await resp.aread()
                log.warning("bedrock_responses_stream_http_error", status=resp.status_code)
                raise UpstreamError()
            async for chunk in resp.aiter_raw():
                yield chunk

    # ── Responses API — SigV4 path ────────────────────────────────────────────

    async def _responses_sigv4(
        self, request: ResponsesRequest, bedrock_model: str, log
    ) -> dict:
        url = self._mantle_url("/responses")
        payload = _build_responses_payload(request, stream=False, provider_model_id=bedrock_model)
        body_bytes = json.dumps(payload).encode()
        headers = self._sign_sigv4_headers("POST", url, body_bytes)
        resp = await self._mantle_client.post(url, content=body_bytes, headers=headers)
        if resp.status_code != 200:
            log.warning("bedrock_responses_sigv4_error", status=resp.status_code, body=resp.text[:200])
            raise UpstreamError()
        body = resp.json()
        _normalize_responses_usage(body)
        return body

    async def _responses_stream_sigv4(
        self, request: ResponsesRequest, bedrock_model: str, log
    ) -> AsyncGenerator[bytes, None]:
        url = self._mantle_url("/responses")
        payload = _build_responses_payload(request, stream=True, provider_model_id=bedrock_model)
        body_bytes = json.dumps(payload).encode()
        headers = self._sign_sigv4_headers("POST", url, body_bytes)
        log.debug("bedrock_responses_stream_open", auth="sigv4")
        async with self._mantle_client.stream(
            "POST", url, content=body_bytes, headers=headers
        ) as resp:
            if resp.status_code != 200:
                await resp.aread()
                log.warning("bedrock_responses_stream_sigv4_error", status=resp.status_code)
                raise UpstreamError()
            async for chunk in resp.aiter_raw():
                yield chunk

    # ── ProviderAdapter: Responses API ────────────────────────────────────────

    async def responses_create(
        self,
        request: ResponsesRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        bedrock_model = provider_model_id or _bedrock_model_id(request.model or "")
        log = logger.bind(model=request.model, bedrock_model=bedrock_model)
        try:
            if self._use_bearer(api_key):
                return await self._responses_http(request, bedrock_model, api_key, log)
            else:
                return await self._responses_sigv4(request, bedrock_model, log)
        except (GatewayTimeoutError, UpstreamError):
            raise
        except Exception as exc:
            err_name = type(exc).__name__
            if "Timeout" in err_name or "timeout" in str(exc).lower():
                log.warning("bedrock_responses_timeout")
                raise GatewayTimeoutError() from exc
            log.warning("bedrock_responses_error", error=str(exc))
            raise UpstreamError() from exc

    async def stream_responses_create(
        self,
        request: ResponsesRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        bedrock_model = provider_model_id or _bedrock_model_id(request.model or "")
        log = logger.bind(model=request.model, bedrock_model=bedrock_model)
        try:
            if self._use_bearer(api_key):
                async for chunk in self._responses_stream_http(
                    request, bedrock_model, api_key, log
                ):
                    yield chunk
            else:
                async for chunk in self._responses_stream_sigv4(
                    request, bedrock_model, log
                ):
                    yield chunk
        except (GatewayTimeoutError, UpstreamError):
            raise
        except Exception as exc:
            err_name = type(exc).__name__
            if "Timeout" in err_name or "timeout" in str(exc).lower():
                log.warning("bedrock_responses_stream_timeout")
                raise GatewayTimeoutError() from exc
            log.warning("bedrock_responses_stream_error", error=str(exc))
            raise UpstreamError() from exc
