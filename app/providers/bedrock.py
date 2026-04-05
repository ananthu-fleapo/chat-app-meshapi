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

logger = structlog.get_logger()

# Canonical model name → AWS Bedrock model ID
_MODEL_MAP: dict[str, str] = {
    "anthropic/claude-3-5-sonnet":                   "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic/claude-3-5-sonnet-20241022":          "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic/claude-3-5-haiku":                    "anthropic.claude-3-5-haiku-20241022-v1:0",
    "anthropic/claude-3-5-haiku-20241022":           "anthropic.claude-3-5-haiku-20241022-v1:0",
    "anthropic/claude-3-opus":                       "anthropic.claude-3-opus-20240229-v1:0",
    "anthropic/claude-3-opus-20240229":              "anthropic.claude-3-opus-20240229-v1:0",
    "anthropic/claude-3-sonnet":                     "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic/claude-3-haiku":                      "anthropic.claude-3-haiku-20240307-v1:0",
    "meta-llama/llama-3.1-70b-instruct":             "meta.llama3-1-70b-instruct-v1:0",
    "meta-llama/llama-3.1-8b-instruct":              "meta.llama3-1-8b-instruct-v1:0",
    "meta-llama/llama-3.1-405b-instruct":            "meta.llama3-1-405b-instruct-v1:0",
    "meta-llama/llama-3.2-1b-instruct":              "meta.llama3-2-1b-instruct-v1:0",
    "meta-llama/llama-3.2-3b-instruct":              "meta.llama3-2-3b-instruct-v1:0",
    "amazon/nova-lite-v1":                           "amazon.nova-lite-v1:0",
    "amazon/nova-micro-v1":                          "amazon.nova-micro-v1:0",
    "amazon/nova-pro-v1":                            "amazon.nova-pro-v1:0",
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
        # Shared httpx client for bearer-token path (connection-pooled)
        self._http_client: httpx.AsyncClient | None = (
            httpx.AsyncClient(timeout=timeout) if api_key else None
        )

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
        if cls._instance and cls._instance._http_client:
            await cls._instance._http_client.aclose()
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
            raise UpstreamError() from exc

        yield b"data: [DONE]\n\n"

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
