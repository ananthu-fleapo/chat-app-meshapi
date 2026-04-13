"""
Tests for the POST /v1/responses endpoint.

Covers:
  ResponsesRequest schema      — field validation, RESPONSES_ONLY_FIELDS
  resolve_responses_config     — model priority, param layering, max_tokens isolation
  _build_responses_payload     — serialisation, stream flag, owner user field,
                                 no stream_options injection
  OpenRouterAdapter            — responses_create success/error/timeout,
                                 stream_responses_create success/error/timeout
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from tests.conftest import make_execute_result


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_httpx_response(status: int, body: dict | str) -> httpx.Response:
    content = json.dumps(body).encode() if isinstance(body, dict) else body.encode()
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/responses")
    return httpx.Response(status_code=status, content=content, request=request)


def _make_stream_response(status: int, chunks: list[bytes]):
    """Async context manager mimicking httpx streaming."""
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


def _make_responses_request(**kwargs):
    from app.schemas.responses import ResponsesRequest
    defaults = {"model": "openai/o4-mini", "input": "What is 2+2?"}
    defaults.update(kwargs)
    return ResponsesRequest(**defaults)


def _make_key(default_model=None, default_params=None):
    key = MagicMock()
    key.default_model = default_model
    key.default_params = default_params or {}
    return key


# ─────────────────────────────────────────────────────────────────────────────
# ResponsesRequest schema
# ─────────────────────────────────────────────────────────────────────────────

class TestResponsesRequestSchema:

    def test_minimal_valid_request(self):
        from app.schemas.responses import ResponsesRequest
        req = ResponsesRequest(model="openai/o4-mini", input="hello")
        assert req.model == "openai/o4-mini"
        assert req.input == "hello"
        assert req.stream is False
        assert req.reasoning is None
        assert req.max_output_tokens is None

    def test_input_accepts_string(self):
        from app.schemas.responses import ResponsesRequest
        req = ResponsesRequest(model="openai/o4-mini", input="a string")
        assert req.input == "a string"

    def test_input_accepts_list(self):
        from app.schemas.responses import ResponsesRequest
        messages = [{"role": "user", "content": "hi"}]
        req = ResponsesRequest(model="openai/o4-mini", input=messages)
        assert req.input == messages

    def test_model_is_optional(self):
        """model=None is allowed — config resolver fills it from key defaults."""
        from app.schemas.responses import ResponsesRequest
        req = ResponsesRequest(input="hi")
        assert req.model is None

    def test_reasoning_field_accepted(self):
        from app.schemas.responses import ResponsesRequest
        req = ResponsesRequest(model="openai/o4-mini", input="hi", reasoning={"effort": "high"})
        assert req.reasoning == {"effort": "high"}

    def test_plugins_field_accepted(self):
        from app.schemas.responses import ResponsesRequest
        req = ResponsesRequest(model="openai/o4-mini", input="hi", plugins=[{"id": "web"}])
        assert req.plugins == [{"id": "web"}]

    def test_max_output_tokens_minimum_enforced(self):
        from app.schemas.responses import ResponsesRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ResponsesRequest(model="openai/o4-mini", input="hi", max_output_tokens=0)

    def test_temperature_bounds_enforced(self):
        from app.schemas.responses import ResponsesRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ResponsesRequest(model="openai/o4-mini", input="hi", temperature=2.5)

    def test_user_max_length_enforced(self):
        from app.schemas.responses import ResponsesRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ResponsesRequest(model="openai/o4-mini", input="hi", user="x" * 257)

    def test_routerv_only_fields_present_in_schema(self):
        """template/variables/session_id are declared on the schema."""
        from app.schemas.responses import ResponsesRequest
        req = ResponsesRequest(
            model="openai/o4-mini",
            input="hi",
            template="my-tmpl",
            variables={"k": "v"},
            session_id="sess-1",
        )
        assert req.template == "my-tmpl"
        assert req.variables == {"k": "v"}
        assert req.session_id == "sess-1"

    def test_responses_only_fields_constant(self):
        from app.schemas.responses import RESPONSES_ONLY_FIELDS
        assert RESPONSES_ONLY_FIELDS == {"template", "variables", "session_id"}

    def test_tools_accepts_function_tool(self):
        from app.schemas.responses import ResponsesRequest
        req = ResponsesRequest(
            model="openai/o4-mini",
            input="hi",
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object", "properties": {}},
                },
            }],
        )
        assert req.tools[0].type == "function"
        assert req.tools[0].function.name == "get_weather"

    def test_invalid_tool_type_raises_validation_error(self):
        from app.schemas.responses import ResponsesRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ResponsesRequest(
                model="openai/o4-mini",
                input="hi",
                tools=[{"type": "unknown_tool"}],
            )


# ─────────────────────────────────────────────────────────────────────────────
# resolve_responses_config
# ─────────────────────────────────────────────────────────────────────────────

class TestResolveResponsesConfig:

    def test_body_model_takes_priority(self):
        from app.auth.config_resolver import resolve_responses_config
        body = _make_responses_request(model="openai/o4-mini")
        key = _make_key(default_model="anthropic/claude-3-haiku")
        result = resolve_responses_config(body, key)
        assert result.model == "openai/o4-mini"

    def test_key_default_model_fills_in_when_body_is_none(self):
        from app.auth.config_resolver import resolve_responses_config
        body = _make_responses_request(model=None)
        key = _make_key(default_model="openai/o4-mini")
        result = resolve_responses_config(body, key)
        assert result.model == "openai/o4-mini"

    def test_no_model_from_any_source_raises_422(self):
        from app.auth.config_resolver import resolve_responses_config
        from app.exceptions import UnprocessableEntityError
        body = _make_responses_request(model=None)
        key = _make_key(default_model=None)
        with pytest.raises(UnprocessableEntityError, match="model is required"):
            resolve_responses_config(body, key)

    def test_body_temperature_overrides_key_default(self):
        from app.auth.config_resolver import resolve_responses_config
        body = _make_responses_request(temperature=0.9)
        key = _make_key(default_params={"temperature": 0.1})
        result = resolve_responses_config(body, key)
        assert result.temperature == 0.9

    def test_key_default_temperature_fills_in_when_body_is_none(self):
        from app.auth.config_resolver import resolve_responses_config
        body = _make_responses_request(temperature=None)
        key = _make_key(default_params={"temperature": 0.4})
        result = resolve_responses_config(body, key)
        assert result.temperature == 0.4

    def test_key_default_max_output_tokens_fills_in(self):
        from app.auth.config_resolver import resolve_responses_config
        body = _make_responses_request(max_output_tokens=None)
        key = _make_key(default_params={"max_output_tokens": 512})
        result = resolve_responses_config(body, key)
        assert result.max_output_tokens == 512

    def test_max_tokens_key_default_does_not_bleed_into_max_output_tokens(self):
        """max_tokens in key.default_params must NOT map to max_output_tokens —
        they are different fields on different API surfaces."""
        from app.auth.config_resolver import resolve_responses_config
        body = _make_responses_request(max_output_tokens=None)
        key = _make_key(default_params={"max_tokens": 1024})
        result = resolve_responses_config(body, key)
        assert result.max_output_tokens is None

    def test_all_mergeable_params_filled_from_key(self):
        from app.auth.config_resolver import resolve_responses_config
        body = _make_responses_request()
        key = _make_key(default_params={
            "temperature": 0.5,
            "max_output_tokens": 256,
            "top_p": 0.9,
            "seed": 42,
        })
        result = resolve_responses_config(body, key)
        assert result.temperature == 0.5
        assert result.max_output_tokens == 256
        assert result.top_p == 0.9
        assert result.seed == 42

    def test_routerv_fields_carried_through(self):
        """template/variables/session_id survive the resolver for later stripping."""
        from app.auth.config_resolver import resolve_responses_config
        from app.schemas.responses import ResponsesRequest
        body = ResponsesRequest(
            model="openai/o4-mini",
            input="hi",
            template="my-tmpl",
            variables={"name": "Alice"},
            session_id="sess-99",
        )
        key = _make_key()
        result = resolve_responses_config(body, key)
        assert result.template == "my-tmpl"
        assert result.variables == {"name": "Alice"}
        assert result.session_id == "sess-99"

    def test_returns_responses_request_instance(self):
        from app.auth.config_resolver import resolve_responses_config
        from app.schemas.responses import ResponsesRequest
        body = _make_responses_request()
        result = resolve_responses_config(body, _make_key())
        assert isinstance(result, ResponsesRequest)


# ─────────────────────────────────────────────────────────────────────────────
# _build_responses_payload
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildResponsesPayload:

    def test_stream_false_sets_stream_false(self):
        from app.providers.openrouter import _build_responses_payload
        req = _make_responses_request()
        payload = _build_responses_payload(req, stream=False, owner=None)
        assert payload["stream"] is False

    def test_stream_true_sets_stream_true(self):
        from app.providers.openrouter import _build_responses_payload
        req = _make_responses_request()
        payload = _build_responses_payload(req, stream=True, owner=None)
        assert payload["stream"] is True

    def test_no_stream_options_injected(self):
        """Responses API sends usage natively — stream_options must NOT be added."""
        from app.providers.openrouter import _build_responses_payload
        req = _make_responses_request()
        payload = _build_responses_payload(req, stream=True, owner=None)
        assert "stream_options" not in payload

    def test_routerv_only_fields_stripped(self):
        from app.providers.openrouter import _build_responses_payload
        from app.schemas.responses import ResponsesRequest
        req = ResponsesRequest(
            model="openai/o4-mini",
            input="hi",
            template="tmpl",
            variables={"k": "v"},
            session_id="sess-1",
        )
        payload = _build_responses_payload(req, stream=False, owner=None)
        assert "template" not in payload
        assert "variables" not in payload
        assert "session_id" not in payload

    def test_none_fields_excluded(self):
        """None-valued fields must not appear in the payload."""
        from app.providers.openrouter import _build_responses_payload
        req = _make_responses_request(reasoning=None, plugins=None, max_output_tokens=None)
        payload = _build_responses_payload(req, stream=False, owner=None)
        assert "reasoning" not in payload
        assert "plugins" not in payload
        assert "max_output_tokens" not in payload

    def test_reasoning_included_when_set(self):
        from app.providers.openrouter import _build_responses_payload
        req = _make_responses_request(reasoning={"effort": "high"})
        payload = _build_responses_payload(req, stream=False, owner=None)
        assert payload["reasoning"] == {"effort": "high"}

    def test_plugins_included_when_set(self):
        from app.providers.openrouter import _build_responses_payload
        req = _make_responses_request(plugins=[{"id": "web", "max_results": 3}])
        payload = _build_responses_payload(req, stream=False, owner=None)
        assert payload["plugins"] == [{"id": "web", "max_results": 3}]

    def test_owner_sets_user_field(self):
        from app.providers.openrouter import _build_responses_payload
        req = _make_responses_request()
        payload = _build_responses_payload(req, stream=False, owner="acme")
        assert payload["user"] == "owner:acme"

    def test_owner_none_does_not_set_user(self):
        from app.providers.openrouter import _build_responses_payload
        req = _make_responses_request()
        payload = _build_responses_payload(req, stream=False, owner=None)
        assert "user" not in payload

    def test_owner_truncated_to_256_chars(self):
        from app.providers.openrouter import _build_responses_payload
        req = _make_responses_request()
        long_owner = "x" * 300
        payload = _build_responses_payload(req, stream=False, owner=long_owner)
        assert len(payload["user"]) == 256

    def test_explicit_user_in_request_not_overridden_by_owner(self):
        """If caller already set user, owner prefix must not clobber it."""
        from app.providers.openrouter import _build_responses_payload
        req = _make_responses_request(user="my-tracker")
        payload = _build_responses_payload(req, stream=False, owner="acme")
        assert payload["user"] == "my-tracker"


# ─────────────────────────────────────────────────────────────────────────────
# OpenRouterAdapter.responses_create
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenRouterAdapterResponsesCreate:

    def _make_adapter(self):
        from app.providers.openrouter import OpenRouterAdapter
        OpenRouterAdapter._instance = None
        return OpenRouterAdapter.init(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
        )

    async def test_success_returns_parsed_json(self):
        adapter = self._make_adapter()
        body = {"id": "resp-1", "choices": [{"message": {"role": "assistant", "content": "4"}}], "usage": {}}
        adapter._client.post = AsyncMock(return_value=_make_httpx_response(200, body))

        result = await adapter.responses_create(_make_responses_request())

        assert result["id"] == "resp-1"

    async def test_posts_to_responses_path(self):
        """Must call /responses, not /chat/completions."""
        adapter = self._make_adapter()
        body = {"id": "resp-1", "choices": [], "usage": {}}
        adapter._client.post = AsyncMock(return_value=_make_httpx_response(200, body))

        await adapter.responses_create(_make_responses_request())
        
        call_args = adapter._client.post.call_args
        assert call_args.args[0] == "/responses"

    async def test_http_error_raises_upstream_error(self):
        from app.exceptions import UpstreamError
        adapter = self._make_adapter()
        adapter._client.post = AsyncMock(
            return_value=_make_httpx_response(429, {"error": "rate limited"})
        )
        with pytest.raises(UpstreamError):
            await adapter.responses_create(_make_responses_request())

    async def test_timeout_raises_gateway_timeout(self):
        from app.exceptions import GatewayTimeoutError
        adapter = self._make_adapter()
        adapter._client.post = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(GatewayTimeoutError):
            await adapter.responses_create(_make_responses_request())

    async def test_per_request_api_key_sent_in_auth_header(self):
        adapter = self._make_adapter()
        body = {"id": "resp-2", "choices": [], "usage": {}}
        adapter._client.post = AsyncMock(return_value=_make_httpx_response(200, body))

        await adapter.responses_create(_make_responses_request(), api_key="owner-key-123")

        call_kwargs = adapter._client.post.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer owner-key-123"}

    async def test_no_api_key_sends_empty_headers(self):
        adapter = self._make_adapter()
        body = {"id": "resp-3", "choices": [], "usage": {}}
        adapter._client.post = AsyncMock(return_value=_make_httpx_response(200, body))

        await adapter.responses_create(_make_responses_request(), api_key=None)

        call_kwargs = adapter._client.post.call_args
        assert call_kwargs.kwargs["headers"] == {}

    async def test_payload_has_no_stream_options(self):
        """responses_create must never inject stream_options into the payload."""
        adapter = self._make_adapter()
        body = {"id": "resp-4", "choices": [], "usage": {}}
        adapter._client.post = AsyncMock(return_value=_make_httpx_response(200, body))

        await adapter.responses_create(_make_responses_request())

        payload = adapter._client.post.call_args.kwargs["json"]
        assert "stream_options" not in payload
        assert payload["stream"] is False

    async def test_reasoning_forwarded_in_payload(self):
        adapter = self._make_adapter()
        body = {"id": "resp-5", "choices": [], "usage": {}}
        adapter._client.post = AsyncMock(return_value=_make_httpx_response(200, body))

        req = _make_responses_request(reasoning={"effort": "high"})
        await adapter.responses_create(req)

        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["reasoning"] == {"effort": "high"}


# ─────────────────────────────────────────────────────────────────────────────
# OpenRouterAdapter.stream_responses_create
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenRouterAdapterStreamResponsesCreate:

    def _make_adapter(self):
        from app.providers.openrouter import OpenRouterAdapter
        OpenRouterAdapter._instance = None
        return OpenRouterAdapter.init(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
        )

    async def test_yields_all_chunks(self):
        adapter = self._make_adapter()
        chunks = [b"data: hello\n\n", b"data: [DONE]\n\n"]
        adapter._client.stream = MagicMock(return_value=_make_stream_response(200, chunks))

        received = []
        async for chunk in adapter.stream_responses_create(_make_responses_request()):
            received.append(chunk)

        assert received == chunks

    async def test_posts_to_responses_path_when_streaming(self):
        """Streaming must also hit /responses, not /chat/completions."""
        adapter = self._make_adapter()
        chunks = [b"data: [DONE]\n\n"]
        mock_stream = _make_stream_response(200, chunks)
        adapter._client.stream = MagicMock(return_value=mock_stream)

        async for _ in adapter.stream_responses_create(_make_responses_request()):
            pass

        call_args = adapter._client.stream.call_args
        assert call_args.args[1] == "/responses"

    async def test_stream_payload_has_stream_true_no_stream_options(self):
        adapter = self._make_adapter()
        chunks = [b"data: [DONE]\n\n"]
        mock_stream = _make_stream_response(200, chunks)
        adapter._client.stream = MagicMock(return_value=mock_stream)

        async for _ in adapter.stream_responses_create(_make_responses_request()):
            pass

        payload = adapter._client.stream.call_args.kwargs["json"]
        assert payload["stream"] is True
        assert "stream_options" not in payload

    async def test_http_error_raises_upstream_error(self):
        from app.exceptions import UpstreamError
        adapter = self._make_adapter()
        adapter._client.stream = MagicMock(return_value=_make_stream_response(401, []))

        with pytest.raises(UpstreamError):
            async for _ in adapter.stream_responses_create(_make_responses_request()):
                pass

    async def test_timeout_raises_gateway_timeout(self):
        from app.exceptions import GatewayTimeoutError
        adapter = self._make_adapter()

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
        cm.__aexit__ = AsyncMock(return_value=False)
        adapter._client.stream = MagicMock(return_value=cm)

        with pytest.raises(GatewayTimeoutError):
            async for _ in adapter.stream_responses_create(_make_responses_request()):
                pass

    async def test_per_request_api_key_sent_in_auth_header(self):
        adapter = self._make_adapter()
        chunks = [b"data: [DONE]\n\n"]
        mock_stream = _make_stream_response(200, chunks)
        adapter._client.stream = MagicMock(return_value=mock_stream)

        async for _ in adapter.stream_responses_create(
            _make_responses_request(), api_key="per-owner-key"
        ):
            pass

        call_kwargs = adapter._client.stream.call_args.kwargs
        assert call_kwargs["headers"] == {"Authorization": "Bearer per-owner-key"}

    async def test_usage_chunk_parseable_from_stream(self):
        """Simulate a Responses API SSE stream that ends with a usage chunk —
        verify the byte content can be parsed by the same logic used in the router."""
        adapter = self._make_adapter()
        usage_chunk = json.dumps({
            "id": "resp-1", "choices": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        })
        chunks = [
            b"data: " + json.dumps({"id": "resp-1", "choices": [{"delta": {"content": "4"}}]}).encode() + b"\n\n",
            b"data: " + usage_chunk.encode() + b"\n\n",
            b"data: [DONE]\n\n",
        ]
        adapter._client.stream = MagicMock(return_value=_make_stream_response(200, chunks))

        received = b""
        async for chunk in adapter.stream_responses_create(_make_responses_request()):
            received += chunk

        # Parse the received bytes with the same logic the router uses
        usage_data = None
        buf = received
        while b"\n\n" in buf:
            frame, buf = buf.split(b"\n\n", 1)
            for line in frame.split(b"\n"):
                if not line.startswith(b"data: "):
                    continue
                payload = line[6:].strip()
                if payload == b"[DONE]":
                    continue
                obj = json.loads(payload)
                if obj.get("usage") and not obj.get("choices"):
                    usage_data = obj["usage"]

        assert usage_data is not None
        assert usage_data["prompt_tokens"] == 10
        assert usage_data["completion_tokens"] == 5
