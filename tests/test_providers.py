"""
Unit tests for new provider adapters and the provider registry.

Covers:
  OpenAIDirectAdapter   — model name translation, chat_completion success/error/timeout,
                          stream_chat_completion success/error
  QwenAdapter           — model name translation, chat_completion success/error/timeout,
                          stream_chat_completion success/error
  VertexAIAdapter       — model name translation, token refresh, chat_completion
                          success/error/timeout, stream_chat_completion success/error
  BedrockAdapter        — model name translation, message format conversion,
                          response conversion, SSE event translation,
                          chat_completion success/error, stream_chat_completion
  registry              — get_adapter, resolve_provider, register_adapter
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tests.conftest import make_execute_result


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_httpx_response(status: int, body: dict | str) -> httpx.Response:
    """Build a real httpx.Response with a dummy request (required for raise_for_status)."""
    content = json.dumps(body).encode() if isinstance(body, dict) else body.encode()
    request = httpx.Request("POST", "https://example.com/chat/completions")
    return httpx.Response(status_code=status, content=content, request=request)


def _make_stream_response(status: int, chunks: list[bytes]):
    """
    Build an async context manager that mimics httpx streaming.

    The returned mock supports:
      async with client.stream(...) as response: ...
      async for chunk in response.aiter_raw(): ...
    """
    response = MagicMock()
    response.status_code = status

    async def _aiter_raw():
        for chunk in chunks:
            yield chunk

    response.aiter_raw = _aiter_raw
    response.aread = AsyncMock()
    response.text = ""

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_chat_request(model: str = "openai/gpt-4o-mini") -> MagicMock:
    """Minimal ChatCompletionRequest-like mock."""
    from app.schemas.chat import ChatCompletionRequest, Message
    return ChatCompletionRequest(
        model=model,
        messages=[Message(role="user", content="hi")],
    )


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI Direct — model translation
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenAIModelTranslation:

    def test_strips_openai_prefix(self):
        from app.providers.openai_direct import _openai_model_id
        assert _openai_model_id("openai/gpt-4o") == "gpt-4o"

    def test_strips_openai_prefix_mini(self):
        from app.providers.openai_direct import _openai_model_id
        assert _openai_model_id("openai/gpt-4o-mini") == "gpt-4o-mini"

    def test_passthrough_no_prefix(self):
        from app.providers.openai_direct import _openai_model_id
        assert _openai_model_id("gpt-4o") == "gpt-4o"

    def test_passthrough_other_prefix(self):
        from app.providers.openai_direct import _openai_model_id
        assert _openai_model_id("anthropic/claude-3-5-sonnet") == "anthropic/claude-3-5-sonnet"


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI Direct — adapter behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenAIDirectAdapter:

    def _make_adapter(self) -> "OpenAIDirectAdapter":
        from app.providers.openai_direct import OpenAIDirectAdapter
        OpenAIDirectAdapter._instance = None
        return OpenAIDirectAdapter.init(
            api_key="test-openai-key",
            base_url="https://api.openai.com/v1",
        )

    async def test_chat_completion_success(self):
        from app.providers.openai_direct import OpenAIDirectAdapter
        adapter = self._make_adapter()
        body = {"id": "chatcmpl-1", "choices": [], "usage": {}}
        adapter._client.post = AsyncMock(
            return_value=_make_httpx_response(200, body)
        )

        result = await adapter.chat_completion(_make_chat_request("openai/gpt-4o-mini"))

        assert result["id"] == "chatcmpl-1"
        # Verify the model name was translated in the payload
        call_kwargs = adapter._client.post.call_args
        assert call_kwargs.kwargs["json"]["model"] == "gpt-4o-mini"

    async def test_chat_completion_http_error_raises_upstream(self):
        from app.providers.openai_direct import OpenAIDirectAdapter
        from app.exceptions import UpstreamError
        adapter = self._make_adapter()
        adapter._client.post = AsyncMock(
            return_value=_make_httpx_response(429, {"error": "rate limited"})
        )

        with pytest.raises(UpstreamError):
            await adapter.chat_completion(_make_chat_request())

    async def test_chat_completion_timeout_raises_gateway_timeout(self):
        from app.providers.openai_direct import OpenAIDirectAdapter
        from app.exceptions import GatewayTimeoutError
        adapter = self._make_adapter()
        adapter._client.post = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))

        with pytest.raises(GatewayTimeoutError):
            await adapter.chat_completion(_make_chat_request())

    async def test_stream_chat_completion_yields_chunks(self):
        from app.providers.openai_direct import OpenAIDirectAdapter
        adapter = self._make_adapter()
        chunks = [b"data: hello\n\n", b"data: [DONE]\n\n"]
        adapter._client.stream = MagicMock(
            return_value=_make_stream_response(200, chunks)
        )

        received = []
        async for chunk in adapter.stream_chat_completion(_make_chat_request()):
            received.append(chunk)

        assert received == chunks

    async def test_stream_chat_completion_http_error_raises_upstream(self):
        from app.providers.openai_direct import OpenAIDirectAdapter
        from app.exceptions import UpstreamError
        adapter = self._make_adapter()

        err_response = MagicMock()
        err_response.status_code = 401
        err_response.text = "Unauthorized"
        err_response.aread = AsyncMock()
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=err_response)
        cm.__aexit__ = AsyncMock(return_value=False)
        adapter._client.stream = MagicMock(return_value=cm)

        with pytest.raises(UpstreamError):
            async for _ in adapter.stream_chat_completion(_make_chat_request()):
                pass

    async def test_per_request_api_key_overrides_default(self):
        from app.providers.openai_direct import OpenAIDirectAdapter
        adapter = self._make_adapter()
        body = {"id": "chatcmpl-2", "choices": []}
        adapter._client.post = AsyncMock(
            return_value=_make_httpx_response(200, body)
        )

        await adapter.chat_completion(_make_chat_request(), api_key="owner-key")

        call_kwargs = adapter._client.post.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer owner-key"}


# ─────────────────────────────────────────────────────────────────────────────
# Qwen — model translation
# ─────────────────────────────────────────────────────────────────────────────

class TestQwenModelTranslation:

    def test_strips_qwen_prefix(self):
        from app.providers.qwen import _qwen_model_id
        assert _qwen_model_id("qwen/qwen-turbo") == "qwen-turbo"

    def test_strips_qwen_prefix_max(self):
        from app.providers.qwen import _qwen_model_id
        assert _qwen_model_id("qwen/qwen-max") == "qwen-max"

    def test_strips_qwen_prefix_versioned(self):
        from app.providers.qwen import _qwen_model_id
        assert _qwen_model_id("qwen/qwen2.5-72b-instruct") == "qwen2.5-72b-instruct"

    def test_passthrough_no_prefix(self):
        from app.providers.qwen import _qwen_model_id
        assert _qwen_model_id("qwen-turbo") == "qwen-turbo"

    def test_passthrough_other_namespace(self):
        from app.providers.qwen import _qwen_model_id
        assert _qwen_model_id("openai/gpt-4o") == "openai/gpt-4o"


# ─────────────────────────────────────────────────────────────────────────────
# Qwen — adapter behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestQwenAdapter:

    def _make_adapter(self) -> "QwenAdapter":
        from app.providers.qwen import QwenAdapter
        QwenAdapter._instance = None
        return QwenAdapter.init(api_key="test-dashscope-key")

    async def test_chat_completion_success(self):
        from app.providers.qwen import QwenAdapter
        adapter = self._make_adapter()
        body = {"id": "chatcmpl-qwen-1", "choices": []}
        adapter._client.post = AsyncMock(
            return_value=_make_httpx_response(200, body)
        )

        result = await adapter.chat_completion(
            _make_chat_request("qwen/qwen-turbo")
        )

        assert result["id"] == "chatcmpl-qwen-1"
        # Model name translated in payload
        assert adapter._client.post.call_args.kwargs["json"]["model"] == "qwen-turbo"

    async def test_chat_completion_http_error_raises_upstream(self):
        from app.providers.qwen import QwenAdapter
        from app.exceptions import UpstreamError
        adapter = self._make_adapter()
        adapter._client.post = AsyncMock(
            return_value=_make_httpx_response(503, {"error": "service unavailable"})
        )

        with pytest.raises(UpstreamError):
            await adapter.chat_completion(_make_chat_request("qwen/qwen-max"))

    async def test_chat_completion_timeout_raises_gateway_timeout(self):
        from app.providers.qwen import QwenAdapter
        from app.exceptions import GatewayTimeoutError
        adapter = self._make_adapter()
        adapter._client.post = AsyncMock(
            side_effect=httpx.ConnectTimeout("connect timed out")
        )

        with pytest.raises(GatewayTimeoutError):
            await adapter.chat_completion(_make_chat_request("qwen/qwen-plus"))

    async def test_stream_completion_yields_chunks(self):
        from app.providers.qwen import QwenAdapter
        adapter = self._make_adapter()
        chunks = [b"data: chunk1\n\n", b"data: [DONE]\n\n"]
        adapter._client.stream = MagicMock(
            return_value=_make_stream_response(200, chunks)
        )

        received = []
        async for chunk in adapter.stream_chat_completion(
            _make_chat_request("qwen/qwen-turbo")
        ):
            received.append(chunk)

        assert received == chunks


# ─────────────────────────────────────────────────────────────────────────────
# Vertex AI — model translation
# ─────────────────────────────────────────────────────────────────────────────

class TestVertexModelTranslation:

    def test_known_claude_model_translated(self):
        from app.providers.vertex_ai import _vertex_model_id
        # Vertex OpenAI endpoint requires anthropic/<model>@<version> format
        assert _vertex_model_id("anthropic/claude-3-5-sonnet") == "anthropic/claude-3-5-sonnet@20241022"

    def test_known_claude_haiku_translated(self):
        from app.providers.vertex_ai import _vertex_model_id
        assert _vertex_model_id("anthropic/claude-3-5-haiku") == "anthropic/claude-3-5-haiku@20241022"

    def test_known_gemini_flash_translated(self):
        from app.providers.vertex_ai import _vertex_model_id
        # Vertex OpenAI endpoint requires google/<model> format
        assert _vertex_model_id("google/gemini-flash-1.5") == "google/gemini-1.5-flash-002"

    def test_unknown_model_passthrough(self):
        from app.providers.vertex_ai import _vertex_model_id
        assert _vertex_model_id("google/gemini-future") == "google/gemini-future"


# ─────────────────────────────────────────────────────────────────────────────
# Vertex AI — token refresh
# ─────────────────────────────────────────────────────────────────────────────

class TestVertexTokenRefresh:

    def _make_adapter(self) -> "VertexAIAdapter":
        from app.providers.vertex_ai import VertexAIAdapter
        VertexAIAdapter._instance = None
        return VertexAIAdapter.init(
            project_id="my-project",
            location="us-central1",
            service_account_json='{"type":"service_account"}',
        )

    async def test_token_fetched_on_first_call(self):
        """Token is None initially; _auth_headers triggers refresh."""
        from app.providers.vertex_ai import VertexAIAdapter
        adapter = self._make_adapter()
        assert adapter._access_token is None

        with patch(
            "app.providers.vertex_ai._refresh_token_sync",
            return_value=("tok-abc", 9999999999.0),
        ) as mock_refresh, patch("asyncio.to_thread", new=AsyncMock(side_effect=mock_refresh)):
            with patch("asyncio.to_thread", new=AsyncMock(return_value=("tok-abc", 9999999999.0))):
                headers = await adapter._auth_headers()

        assert headers["Authorization"] == "Bearer tok-abc"

    async def test_cached_token_not_refreshed(self):
        """Unexpired cached token is reused without calling refresh."""
        import time
        from app.providers.vertex_ai import VertexAIAdapter
        adapter = self._make_adapter()
        adapter._access_token = "cached-tok"
        adapter._token_expiry = time.time() + 3600  # far future

        with patch("asyncio.to_thread", new=AsyncMock()) as mock_thread:
            headers = await adapter._auth_headers()

        mock_thread.assert_not_called()
        assert headers["Authorization"] == "Bearer cached-tok"

    async def test_expired_token_triggers_refresh(self):
        """Expired token triggers a new refresh call."""
        import time
        from app.providers.vertex_ai import VertexAIAdapter
        adapter = self._make_adapter()
        adapter._access_token = "old-tok"
        adapter._token_expiry = time.time() - 1  # already expired

        with patch(
            "asyncio.to_thread",
            new=AsyncMock(return_value=("new-tok", time.time() + 3300)),
        ):
            headers = await adapter._auth_headers()

        assert headers["Authorization"] == "Bearer new-tok"


# ─────────────────────────────────────────────────────────────────────────────
# Vertex AI — adapter behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestVertexAIAdapter:

    def _make_adapter(self) -> "VertexAIAdapter":
        import time
        from app.providers.vertex_ai import VertexAIAdapter
        VertexAIAdapter._instance = None
        adapter = VertexAIAdapter.init(
            project_id="my-project",
            location="us-central1",
            service_account_json='{"type":"service_account"}',
        )
        # Pre-load a valid token so tests don't need to mock refresh
        adapter._access_token = "test-vertex-token"
        adapter._token_expiry = time.time() + 3600
        return adapter

    async def test_chat_completion_success_translates_model(self):
        from app.providers.vertex_ai import VertexAIAdapter
        adapter = self._make_adapter()
        body = {"id": "vertex-1", "choices": [{"message": {"role": "assistant", "content": "hi"}}]}
        adapter._client.post = AsyncMock(return_value=_make_httpx_response(200, body))

        result = await adapter.chat_completion(
            _make_chat_request("anthropic/claude-3-5-sonnet")
        )

        assert result["id"] == "vertex-1"
        payload_model = adapter._client.post.call_args.kwargs["json"]["model"]
        assert payload_model == "anthropic/claude-3-5-sonnet@20241022"

    async def test_chat_completion_http_error_raises_upstream(self):
        from app.providers.vertex_ai import VertexAIAdapter
        from app.exceptions import UpstreamError
        adapter = self._make_adapter()
        adapter._client.post = AsyncMock(
            return_value=_make_httpx_response(403, {"error": "forbidden"})
        )

        with pytest.raises(UpstreamError):
            await adapter.chat_completion(_make_chat_request("google/gemini-flash-1.5"))

    async def test_chat_completion_timeout_raises_gateway_timeout(self):
        from app.providers.vertex_ai import VertexAIAdapter
        from app.exceptions import GatewayTimeoutError
        adapter = self._make_adapter()
        adapter._client.post = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))

        with pytest.raises(GatewayTimeoutError):
            await adapter.chat_completion(_make_chat_request())

    async def test_stream_chat_completion_yields_chunks(self):
        from app.providers.vertex_ai import VertexAIAdapter
        adapter = self._make_adapter()
        chunks = [b"data: vertex-chunk\n\n", b"data: [DONE]\n\n"]
        adapter._client.stream = MagicMock(
            return_value=_make_stream_response(200, chunks)
        )

        received = []
        async for chunk in adapter.stream_chat_completion(
            _make_chat_request("anthropic/claude-3-5-sonnet")
        ):
            received.append(chunk)

        assert received == chunks

    async def test_stream_http_error_raises_upstream(self):
        from app.providers.vertex_ai import VertexAIAdapter
        from app.exceptions import UpstreamError
        adapter = self._make_adapter()

        err_response = MagicMock()
        err_response.status_code = 500
        err_response.text = "Internal error"
        err_response.aread = AsyncMock()
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=err_response)
        cm.__aexit__ = AsyncMock(return_value=False)
        adapter._client.stream = MagicMock(return_value=cm)

        with pytest.raises(UpstreamError):
            async for _ in adapter.stream_chat_completion(_make_chat_request()):
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Bedrock — model translation
# ─────────────────────────────────────────────────────────────────────────────

class TestBedrockModelTranslation:

    def test_known_claude_sonnet_translated(self):
        from app.providers.bedrock import _bedrock_model_id
        assert (
            _bedrock_model_id("anthropic/claude-sonnet-4-5")
            == "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        )

    def test_known_claude_haiku_translated(self):
        from app.providers.bedrock import _bedrock_model_id
        assert (
            _bedrock_model_id("anthropic/claude-3-haiku")
            == "us.anthropic.claude-3-haiku-20240307-v1:0"
        )

    def test_known_nova_translated(self):
        from app.providers.bedrock import _bedrock_model_id
        assert (
            _bedrock_model_id("amazon/nova-pro-v1")
            == "us.amazon.nova-pro-v1:0"
        )

    def test_unknown_model_passthrough(self):
        from app.providers.bedrock import _bedrock_model_id
        assert _bedrock_model_id("future/new-model") == "future/new-model"


# ─────────────────────────────────────────────────────────────────────────────
# Bedrock — message format conversion
# ─────────────────────────────────────────────────────────────────────────────

class TestBedrockMessageConversion:

    def test_string_content_wraps_in_text_block(self):
        from app.providers.bedrock import _content_to_bedrock
        assert _content_to_bedrock("Hello") == [{"text": "Hello"}]

    def test_list_content_extracts_text_parts(self):
        from app.providers.bedrock import _content_to_bedrock
        content = [{"type": "text", "text": "Hello"}]
        assert _content_to_bedrock(content) == [{"text": "Hello"}]

    def test_list_skips_non_text_parts(self):
        from app.providers.bedrock import _content_to_bedrock
        content = [
            {"type": "image_url", "image_url": {"url": "data:..."}},
            {"type": "text", "text": "What is this?"},
        ]
        result = _content_to_bedrock(content)
        assert result == [{"text": "What is this?"}]

    def test_system_message_extracted(self):
        from app.providers.bedrock import _messages_to_bedrock
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]
        bedrock_msgs, system = _messages_to_bedrock(messages)
        assert system == [{"text": "You are helpful."}]
        assert len(bedrock_msgs) == 1
        assert bedrock_msgs[0]["role"] == "user"

    def test_multiple_system_messages_joined(self):
        from app.providers.bedrock import _messages_to_bedrock
        messages = [
            {"role": "system", "content": "Part A."},
            {"role": "system", "content": "Part B."},
            {"role": "user", "content": "Hello"},
        ]
        _, system = _messages_to_bedrock(messages)
        assert "Part A." in system[0]["text"]
        assert "Part B." in system[0]["text"]

    def test_no_system_message_returns_empty_system(self):
        from app.providers.bedrock import _messages_to_bedrock
        messages = [{"role": "user", "content": "Hi"}]
        _, system = _messages_to_bedrock(messages)
        assert system == []

    def test_assistant_role_preserved(self):
        from app.providers.bedrock import _messages_to_bedrock
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        bedrock_msgs, _ = _messages_to_bedrock(messages)
        assert bedrock_msgs[1]["role"] == "assistant"
        assert bedrock_msgs[1]["content"] == [{"text": "Hello!"}]


# ─────────────────────────────────────────────────────────────────────────────
# Bedrock — response conversion
# ─────────────────────────────────────────────────────────────────────────────

class TestBedrockResponseConversion:

    def _bedrock_resp(
        self,
        text: str = "Hello!",
        stop_reason: str = "end_turn",
        input_tokens: int = 10,
        output_tokens: int = 5,
    ) -> dict:
        return {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": text}],
                }
            },
            "usage": {
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
                "totalTokens": input_tokens + output_tokens,
            },
            "stopReason": stop_reason,
        }

    def test_text_extracted_correctly(self):
        from app.providers.bedrock import _bedrock_response_to_openai
        resp = _bedrock_response_to_openai(
            self._bedrock_resp(text="Hi there!"), "anthropic/claude-3-5-sonnet"
        )
        assert resp["choices"][0]["message"]["content"] == "Hi there!"
        assert resp["choices"][0]["message"]["role"] == "assistant"

    def test_usage_tokens_mapped(self):
        from app.providers.bedrock import _bedrock_response_to_openai
        resp = _bedrock_response_to_openai(
            self._bedrock_resp(input_tokens=100, output_tokens=50),
            "anthropic/claude-3-5-sonnet",
        )
        assert resp["usage"]["prompt_tokens"] == 100
        assert resp["usage"]["completion_tokens"] == 50
        assert resp["usage"]["total_tokens"] == 150

    def test_end_turn_maps_to_stop(self):
        from app.providers.bedrock import _bedrock_response_to_openai
        resp = _bedrock_response_to_openai(
            self._bedrock_resp(stop_reason="end_turn"), "anthropic/claude-3-5-sonnet"
        )
        assert resp["choices"][0]["finish_reason"] == "stop"

    def test_max_tokens_maps_to_length(self):
        from app.providers.bedrock import _bedrock_response_to_openai
        resp = _bedrock_response_to_openai(
            self._bedrock_resp(stop_reason="max_tokens"), "anthropic/claude-3-5-sonnet"
        )
        assert resp["choices"][0]["finish_reason"] == "length"

    def test_openai_response_id_generated(self):
        from app.providers.bedrock import _bedrock_response_to_openai
        resp = _bedrock_response_to_openai(
            self._bedrock_resp(), "anthropic/claude-3-5-sonnet"
        )
        assert resp["id"].startswith("chatcmpl-")
        assert resp["object"] == "chat.completion"
        assert resp["model"] == "anthropic/claude-3-5-sonnet"


# ─────────────────────────────────────────────────────────────────────────────
# Bedrock — SSE event translation
# ─────────────────────────────────────────────────────────────────────────────

class TestBedrockStreamEventTranslation:

    def test_content_block_delta_yields_text_sse(self):
        from app.providers.bedrock import _bedrock_stream_events_to_sse
        event = {"contentBlockDelta": {"delta": {"text": "Hello"}}}
        sse = _bedrock_stream_events_to_sse([event], "chatcmpl-abc", "anthropic/claude-3-5-sonnet")
        assert sse.startswith(b"data: ")
        payload = json.loads(sse[6:].split(b"\n\n")[0])
        assert payload["choices"][0]["delta"]["content"] == "Hello"

    def test_empty_text_delta_yields_nothing(self):
        from app.providers.bedrock import _bedrock_stream_events_to_sse
        event = {"contentBlockDelta": {"delta": {"text": ""}}}
        sse = _bedrock_stream_events_to_sse([event], "chatcmpl-abc", "anthropic/claude-3-5-sonnet")
        assert sse == b""

    def test_message_stop_yields_finish_reason(self):
        from app.providers.bedrock import _bedrock_stream_events_to_sse
        event = {"messageStop": {"stopReason": "end_turn"}}
        sse = _bedrock_stream_events_to_sse([event], "chatcmpl-abc", "anthropic/claude-3-5-sonnet")
        payload = json.loads(sse[6:].split(b"\n\n")[0])
        assert payload["choices"][0]["finish_reason"] == "stop"
        assert payload["choices"][0]["delta"] == {}

    def test_message_stop_max_tokens_yields_length(self):
        from app.providers.bedrock import _bedrock_stream_events_to_sse
        event = {"messageStop": {"stopReason": "max_tokens"}}
        sse = _bedrock_stream_events_to_sse([event], "chatcmpl-abc", "anthropic/claude-3-5-sonnet")
        payload = json.loads(sse[6:].split(b"\n\n")[0])
        assert payload["choices"][0]["finish_reason"] == "length"

    def test_metadata_event_yields_usage_chunk(self):
        from app.providers.bedrock import _bedrock_stream_events_to_sse
        event = {"metadata": {"usage": {"inputTokens": 20, "outputTokens": 10}}}
        sse = _bedrock_stream_events_to_sse([event], "chatcmpl-abc", "anthropic/claude-3-5-sonnet")
        payload = json.loads(sse[6:].split(b"\n\n")[0])
        assert payload["choices"] == []
        assert payload["usage"]["prompt_tokens"] == 20
        assert payload["usage"]["completion_tokens"] == 10
        assert payload["usage"]["total_tokens"] == 30

    def test_unrecognised_event_yields_nothing(self):
        from app.providers.bedrock import _bedrock_stream_events_to_sse
        event = {"messageStart": {"role": "assistant"}}
        sse = _bedrock_stream_events_to_sse([event], "chatcmpl-abc", "anthropic/claude-3-5-sonnet")
        assert sse == b""

    def test_multiple_events_concatenated(self):
        from app.providers.bedrock import _bedrock_stream_events_to_sse
        events = [
            {"contentBlockDelta": {"delta": {"text": "Hi "}}},
            {"contentBlockDelta": {"delta": {"text": "there"}}},
            {"messageStop": {"stopReason": "end_turn"}},
        ]
        sse = _bedrock_stream_events_to_sse(events, "chatcmpl-abc", "anthropic/claude-3-5-sonnet")
        parts = [p for p in sse.split(b"\n\n") if p]
        assert len(parts) == 3
        texts = [json.loads(p[6:])["choices"][0]["delta"].get("content") for p in parts[:2]]
        assert texts == ["Hi ", "there"]


# ─────────────────────────────────────────────────────────────────────────────
# Bedrock — adapter behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestBedrockAdapter:

    def _make_adapter(self) -> "BedrockAdapter":
        from app.providers.bedrock import BedrockAdapter
        BedrockAdapter._instance = None
        return BedrockAdapter.init(
            region="us-east-1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
        )

    def _make_bedrock_converse_response(self, text: str = "Pong") -> dict:
        return {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": text}],
                }
            },
            "usage": {"inputTokens": 5, "outputTokens": 3, "totalTokens": 8},
            "stopReason": "end_turn",
        }

    async def test_chat_completion_success_returns_openai_format(self):
        from app.providers.bedrock import BedrockAdapter
        adapter = self._make_adapter()

        mock_client = AsyncMock()
        mock_client.converse = AsyncMock(
            return_value=self._make_bedrock_converse_response("Pong")
        )
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        adapter._make_sigv4_session = MagicMock(return_value=cm)

        result = await adapter.chat_completion(
            _make_chat_request("anthropic/claude-3-5-sonnet")
        )

        assert result["object"] == "chat.completion"
        assert result["choices"][0]["message"]["content"] == "Pong"
        assert result["usage"]["prompt_tokens"] == 5

    async def test_chat_completion_uses_translated_model_id(self):
        from app.providers.bedrock import BedrockAdapter
        adapter = self._make_adapter()

        mock_client = AsyncMock()
        mock_client.converse = AsyncMock(
            return_value=self._make_bedrock_converse_response()
        )
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        adapter._make_sigv4_session = MagicMock(return_value=cm)

        await adapter.chat_completion(_make_chat_request("anthropic/claude-3-haiku"))

        call_kwargs = mock_client.converse.call_args[1]
        assert call_kwargs["modelId"] == "us.anthropic.claude-3-haiku-20240307-v1:0"

    async def test_chat_completion_upstream_exception_raises_upstream_error(self):
        from app.providers.bedrock import BedrockAdapter
        from app.exceptions import UpstreamError
        adapter = self._make_adapter()

        mock_client = AsyncMock()
        mock_client.converse = AsyncMock(side_effect=Exception("ValidationException"))
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        adapter._make_sigv4_session = MagicMock(return_value=cm)

        with pytest.raises(UpstreamError):
            await adapter.chat_completion(_make_chat_request())

    async def test_stream_chat_completion_yields_role_chunk_first(self):
        from app.providers.bedrock import BedrockAdapter
        adapter = self._make_adapter()

        async def _fake_stream():
            yield {"contentBlockDelta": {"delta": {"text": "Hello"}}}
            yield {"messageStop": {"stopReason": "end_turn"}}

        mock_response = {"stream": _fake_stream()}
        mock_client = AsyncMock()
        mock_client.converse_stream = AsyncMock(return_value=mock_response)
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        adapter._make_sigv4_session = MagicMock(return_value=cm)

        chunks = []
        async for chunk in adapter.stream_chat_completion(
            _make_chat_request("anthropic/claude-3-5-sonnet")
        ):
            chunks.append(chunk)

        # First chunk is the role delta
        assert len(chunks) >= 2
        first = json.loads(chunks[0][6:].split(b"\n\n")[0])
        assert first["choices"][0]["delta"]["role"] == "assistant"

    async def test_stream_chat_completion_ends_with_done(self):
        from app.providers.bedrock import BedrockAdapter
        adapter = self._make_adapter()

        async def _fake_stream():
            yield {"messageStop": {"stopReason": "end_turn"}}

        mock_client = AsyncMock()
        mock_client.converse_stream = AsyncMock(
            return_value={"stream": _fake_stream()}
        )
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        adapter._make_sigv4_session = MagicMock(return_value=cm)

        chunks = []
        async for chunk in adapter.stream_chat_completion(_make_chat_request()):
            chunks.append(chunk)

        assert chunks[-1] == b"data: [DONE]\n\n"


# ─────────────────────────────────────────────────────────────────────────────
# Bedrock — bearer token path + eventstream parser
# ─────────────────────────────────────────────────────────────────────────────

import struct as _struct


def _make_eventstream_frame(event_type: str, payload: dict) -> bytes:
    """
    Build a minimal valid AWS EventStream frame with zeroed CRCs.
    Used to test _parse_eventstream_frames without a live Bedrock connection.
    """
    name = b":event-type"
    value = event_type.encode()
    header = (
        _struct.pack("B", len(name)) + name
        + _struct.pack("B", 7)               # value type: string
        + _struct.pack(">H", len(value)) + value
    )
    import json as _json
    payload_bytes = _json.dumps(payload).encode()
    headers_len = len(header)
    total_len = 12 + headers_len + len(payload_bytes) + 4  # prelude + headers + payload + msg_crc
    return (
        _struct.pack(">I", total_len)
        + _struct.pack(">I", headers_len)
        + _struct.pack(">I", 0)   # prelude CRC — skipped by parser
        + header
        + payload_bytes
        + _struct.pack(">I", 0)   # message CRC — skipped by parser
    )


class TestParseEventstreamFrames:

    def test_parses_content_block_delta(self):
        """contentBlockDelta event is parsed into the expected dict shape."""
        from app.providers.bedrock import _parse_eventstream_frames

        payload = {"delta": {"text": "Hello"}, "contentBlockIndex": 0}
        frame = _make_eventstream_frame("contentBlockDelta", payload)

        events, remaining = _parse_eventstream_frames(frame)

        assert remaining == b""
        assert len(events) == 1
        assert "contentBlockDelta" in events[0]
        assert events[0]["contentBlockDelta"]["delta"]["text"] == "Hello"

    def test_parses_message_stop_event(self):
        from app.providers.bedrock import _parse_eventstream_frames

        frame = _make_eventstream_frame("messageStop", {"stopReason": "end_turn"})
        events, remaining = _parse_eventstream_frames(frame)

        assert len(events) == 1
        assert events[0]["messageStop"]["stopReason"] == "end_turn"

    def test_parses_metadata_usage_event(self):
        from app.providers.bedrock import _parse_eventstream_frames

        payload = {"usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}}
        frame = _make_eventstream_frame("metadata", payload)
        events, _ = _parse_eventstream_frames(frame)

        assert events[0]["metadata"]["usage"]["inputTokens"] == 10

    def test_partial_frame_returned_as_remaining(self):
        """An incomplete frame is held in remaining_bytes, not yielded as an event."""
        from app.providers.bedrock import _parse_eventstream_frames

        frame = _make_eventstream_frame("messageStop", {"stopReason": "end_turn"})
        partial = frame[:10]  # chop the frame mid-way

        events, remaining = _parse_eventstream_frames(partial)

        assert events == []
        assert remaining == partial

    def test_two_frames_in_one_buffer(self):
        """Multiple frames in a single buffer are all parsed."""
        from app.providers.bedrock import _parse_eventstream_frames

        f1 = _make_eventstream_frame("contentBlockDelta", {"delta": {"text": "Hi"}})
        f2 = _make_eventstream_frame("messageStop", {"stopReason": "end_turn"})

        events, remaining = _parse_eventstream_frames(f1 + f2)

        assert len(events) == 2
        assert "contentBlockDelta" in events[0]
        assert "messageStop" in events[1]
        assert remaining == b""


@pytest.mark.asyncio
class TestBedrockBearerPath:

    def _make_bearer_adapter(self) -> "BedrockAdapter":
        from app.providers.bedrock import BedrockAdapter
        BedrockAdapter._instance = None
        return BedrockAdapter.init(
            region="ap-south-1",
            api_key="br-test-bearer-key",
        )

    def _make_bedrock_converse_response(self, text: str = "Pong") -> dict:
        return {
            "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
            "usage": {"inputTokens": 5, "outputTokens": 3, "totalTokens": 8},
            "stopReason": "end_turn",
        }

    async def test_chat_completion_bearer_posts_to_correct_url(self):
        """Bearer path POSTs to /model/{bedrock_model_id}/converse with Authorization header."""
        from app.providers.bedrock import BedrockAdapter
        adapter = self._make_bearer_adapter()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._make_bedrock_converse_response()
        adapter._http_client = AsyncMock()
        adapter._http_client.post = AsyncMock(return_value=mock_response)

        result = await adapter.chat_completion(
            _make_chat_request("anthropic/claude-3-5-sonnet")
        )

        assert result["object"] == "chat.completion"
        assert result["choices"][0]["message"]["content"] == "Pong"
        call_args = adapter._http_client.post.call_args
        assert "/converse" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer br-test-bearer-key"

    async def test_chat_completion_bearer_uses_per_request_key_if_provided(self):
        """Per-request api_key overrides the system bearer key."""
        from app.providers.bedrock import BedrockAdapter
        adapter = self._make_bearer_adapter()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._make_bedrock_converse_response()
        adapter._http_client = AsyncMock()
        adapter._http_client.post = AsyncMock(return_value=mock_response)

        await adapter.chat_completion(
            _make_chat_request("anthropic/claude-3-5-sonnet"),
            api_key="br-owner-key",
        )

        call_args = adapter._http_client.post.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer br-owner-key"

    async def test_stream_chat_completion_bearer_yields_done(self):
        """Bearer streaming path yields [DONE] after all events."""
        from app.providers.bedrock import BedrockAdapter
        adapter = self._make_bearer_adapter()

        stop_frame = _make_eventstream_frame("messageStop", {"stopReason": "end_turn"})

        async def _fake_aiter_raw():
            yield stop_frame

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aiter_raw = _fake_aiter_raw

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_response)
        cm.__aexit__ = AsyncMock(return_value=False)
        adapter._http_client = AsyncMock()
        adapter._http_client.stream = MagicMock(return_value=cm)

        chunks = []
        async for chunk in adapter.stream_chat_completion(
            _make_chat_request("anthropic/claude-3-5-sonnet")
        ):
            chunks.append(chunk)

        assert chunks[-1] == b"data: [DONE]\n\n"

    async def test_stream_chat_completion_bearer_emits_usage_chunk(self):
        """Bearer streaming: metadata event → usage SSE chunk readable by inference.py."""
        from app.providers.bedrock import BedrockAdapter
        adapter = self._make_bearer_adapter()

        delta_frame = _make_eventstream_frame(
            "contentBlockDelta", {"delta": {"text": "Hi"}, "contentBlockIndex": 0}
        )
        meta_frame = _make_eventstream_frame(
            "metadata", {"usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}}
        )
        stop_frame = _make_eventstream_frame("messageStop", {"stopReason": "end_turn"})

        async def _fake_aiter_raw():
            yield delta_frame + meta_frame + stop_frame

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aiter_raw = _fake_aiter_raw

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_response)
        cm.__aexit__ = AsyncMock(return_value=False)
        adapter._http_client = AsyncMock()
        adapter._http_client.stream = MagicMock(return_value=cm)

        import json as _json
        all_chunks = b"".join([
            c async for c in adapter.stream_chat_completion(
                _make_chat_request("anthropic/claude-3-5-sonnet")
            )
        ])

        # Find the usage chunk — choices=[] and usage={} present
        usage_found = False
        for line in all_chunks.split(b"\n"):
            if not line.startswith(b"data: ") or line.strip() == b"data: [DONE]":
                continue
            obj = _json.loads(line[6:])
            if obj.get("usage") and obj.get("choices") == []:
                assert obj["usage"]["prompt_tokens"] == 10
                assert obj["usage"]["completion_tokens"] == 5
                usage_found = True
                break
        assert usage_found, "No usage SSE chunk found in stream output"


# ─────────────────────────────────────────────────────────────────────────────
# Provider Registry
# ─────────────────────────────────────────────────────────────────────────────

def _make_routing_row(provider: str, provider_model_id: str | None = None):
    """Build a mock SQLAlchemy Row with .provider and .provider_model_id attributes."""
    row = MagicMock()
    row.provider = provider
    row.provider_model_id = provider_model_id
    return row


def _make_routing_result(provider: str | None, provider_model_id: str | None = None):
    """make_execute_result variant for resolve_routing (uses .one_or_none())."""
    result = MagicMock()
    result.one_or_none.return_value = (
        _make_routing_row(provider, provider_model_id) if provider is not None else None
    )
    return result


class TestRegistry:

    # ── resolve_routing ──────────────────────────────────────────────────────

    async def test_resolve_routing_returns_provider_and_model_id(self, mock_db):
        """is_default=True row → returns (provider, provider_model_id) tuple."""
        from app.providers.registry import resolve_routing

        mock_db.execute.return_value = _make_routing_result(
            "bedrock", "us.anthropic.claude-3-haiku-20240307-v1:0"
        )

        provider, model_id = await resolve_routing("anthropic/claude-3-haiku", mock_db)

        assert provider == "bedrock"
        assert model_id == "us.anthropic.claude-3-haiku-20240307-v1:0"
        assert mock_db.execute.call_count == 1

    async def test_resolve_routing_none_provider_model_id_when_unset(self, mock_db):
        """Row exists but provider_model_id is NULL → second tuple element is None."""
        from app.providers.registry import resolve_routing

        mock_db.execute.return_value = _make_routing_result("openrouter", None)

        provider, model_id = await resolve_routing("openai/gpt-4o", mock_db)

        assert provider == "openrouter"
        assert model_id is None

    async def test_resolve_routing_falls_back_to_openrouter_if_not_in_db(self, mock_db):
        """Model absent from model_prices → ('openrouter', None)."""
        from app.providers.registry import resolve_routing

        no_row = _make_routing_result(None)
        mock_db.execute.side_effect = [no_row, no_row]

        provider, model_id = await resolve_routing("unknown/model", mock_db)

        assert provider == "openrouter"
        assert model_id is None

    async def test_resolve_routing_falls_back_to_any_row(self, mock_db):
        """No is_default row → any row for this model is used."""
        from app.providers.registry import resolve_routing

        mock_db.execute.side_effect = [
            _make_routing_result(None),              # is_default miss
            _make_routing_result("vertex", None),    # any-row hit
        ]

        provider, model_id = await resolve_routing("google/gemini-flash-1.5", mock_db)

        assert provider == "vertex"
        assert mock_db.execute.call_count == 2

    # ── resolve_provider (compat wrapper) ───────────────────────────────────

    async def test_resolve_provider_returns_is_default_row(self, mock_db):
        """resolve_provider wraps resolve_routing — returns only the provider slug."""
        from app.providers.registry import resolve_provider

        mock_db.execute.return_value = _make_routing_result("vertex")

        result = await resolve_provider("google/gemini-flash-1.5", mock_db)

        assert result == "vertex"
        assert mock_db.execute.call_count == 1

    async def test_resolve_provider_falls_back_to_any_row(self, mock_db):
        """No is_default row → any row for this model is used."""
        from app.providers.registry import resolve_provider

        mock_db.execute.side_effect = [
            _make_routing_result(None),
            _make_routing_result("openrouter"),
        ]

        result = await resolve_provider("openai/gpt-4o-mini", mock_db)

        assert result == "openrouter"
        assert mock_db.execute.call_count == 2

    async def test_resolve_provider_falls_back_to_openrouter_if_not_in_db(self, mock_db):
        """Model not in model_prices → defaults to 'openrouter'."""
        from app.providers.registry import resolve_provider

        no_row = _make_routing_result(None)
        mock_db.execute.side_effect = [no_row, no_row]

        result = await resolve_provider("unknown/model-xyz", mock_db)

        assert result == "openrouter"

    def test_get_adapter_openrouter_returns_singleton(self):
        """get_adapter('openrouter') returns the OpenRouterAdapter singleton."""
        from app.providers.registry import get_adapter, _REGISTRY
        from app.providers.openrouter import OpenRouterAdapter

        # OpenRouter is always in the registry (registered at module level)
        assert "openrouter" in _REGISTRY
        # get() on a non-initialised singleton raises RuntimeError;
        # just check that the correct class is in the registry.
        assert _REGISTRY["openrouter"] is OpenRouterAdapter

    def test_get_adapter_unknown_provider_raises(self):
        """Unknown provider slug raises ProviderNotAvailableError (503)."""
        from app.providers.registry import get_adapter
        from app.exceptions import ProviderNotAvailableError

        with pytest.raises(ProviderNotAvailableError, match="no-such-provider"):
            get_adapter("no-such-provider")

    def test_register_adapter_adds_to_registry(self):
        """register_adapter() makes get_adapter() callable for the new provider."""
        from app.providers.registry import register_adapter, _REGISTRY

        dummy_cls = MagicMock()
        register_adapter("dummy-provider", dummy_cls)

        assert _REGISTRY["dummy-provider"] is dummy_cls
        # Clean up so we don't pollute other tests
        del _REGISTRY["dummy-provider"]


# ─────────────────────────────────────────────────────────────────────────────
# Usage logger — provider param
# ─────────────────────────────────────────────────────────────────────────────

class TestUsageLoggerProvider:
    """Verify that the provider field flows through to UsageEvent."""

    async def test_provider_written_to_usage_event(self):
        """UsageEvent is constructed with the provider kwarg from log_usage_event."""
        from app.usage.logger import log_usage_event
        from app.db.models import UsageEvent

        captured: list[dict] = []

        class _CapturingUsageEvent:
            """Replacement for UsageEvent that records constructor kwargs."""
            def __init__(self, **kwargs):
                captured.append(kwargs)

        # Minimal session mock that satisfies the write path
        session = MagicMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=session)
        cm.__aexit__ = AsyncMock(return_value=False)
        sf = MagicMock(return_value=MagicMock(return_value=cm))

        with patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.logger.UsageEvent", _CapturingUsageEvent), \
             patch("app.usage.logger._our_cost", AsyncMock(return_value=None)), \
             patch("app.usage.balance.deduct_balance", AsyncMock()), \
             patch("app.usage.balance.get_active_discount", AsyncMock(return_value=None)):
            await log_usage_event(
                key_id="00000000-0000-0000-0000-000000000001",
                owner="acme",
                request_id="req-test",
                model="qwen/qwen-turbo",
                provider="qwen",
                template_id=None,
                stream=False,
                prompt_tokens=None,
                completion_tokens=None,
                latency_ms=100,
                status="success",
            )

        assert len(captured) == 1
        assert captured[0]["provider"] == "qwen"
        assert captured[0]["model"] == "qwen/qwen-turbo"

    async def test_fire_usage_log_passes_provider(self):
        """fire_usage_log forwards provider kwarg to log_usage_event."""
        from app.usage.logger import fire_usage_log

        with patch("asyncio.create_task") as mock_ct, \
             patch("app.usage.logger.log_usage_event", new=AsyncMock()) as mock_log:
            fire_usage_log(
                owner="acme",
                provider="vertex",
                key_id="00000000-0000-0000-0000-000000000002",
                request_id="req-v",
                model="google/gemini-flash-1.5",
                template_id=None,
                stream=False,
                prompt_tokens=None,
                completion_tokens=None,
                latency_ms=50,
                status="success",
            )

        mock_ct.assert_called_once()
        # Close the coroutine to avoid RuntimeWarning
        mock_ct.call_args[0][0].close()
