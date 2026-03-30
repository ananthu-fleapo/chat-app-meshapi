"""
Unit tests for app/auth/config_resolver.py

Covers:
  resolve_config — 3-layer priority (body > key > template),
                   model fallback chain, message prepending,
                   structural fields (tools/tool_choice/stream) never pulled from defaults
"""

from unittest.mock import MagicMock

import pytest

from app.auth.config_resolver import resolve_config
from app.exceptions import UnprocessableEntityError
from app.schemas.chat import ChatCompletionRequest, Message


def _make_key(default_model=None, default_params=None):
    key = MagicMock()
    key.default_model = default_model
    key.default_params = default_params or {}
    return key


def _make_template(model=None, params=None):
    tmpl = MagicMock()
    tmpl.model = model
    tmpl.params = params or {}
    return tmpl


def _make_body(**kwargs):
    defaults = {
        "model": None,
        "messages": [Message(role="user", content="hello")],
    }
    defaults.update(kwargs)
    return ChatCompletionRequest(**defaults)


class TestModelPriority:

    def test_body_model_takes_priority_over_key_default(self):
        """Request body model overrides the key's default_model."""
        body = _make_body(model="openai/gpt-4o")
        key = _make_key(default_model="anthropic/claude-3-haiku")
        result = resolve_config(body, key)
        assert result.model == "openai/gpt-4o"

    def test_key_default_used_when_body_has_no_model(self):
        """Key default_model fills in when body.model is None."""
        body = _make_body(model=None)
        key = _make_key(default_model="anthropic/claude-3-haiku")
        result = resolve_config(body, key)
        assert result.model == "anthropic/claude-3-haiku"

    def test_template_model_used_when_body_and_key_have_no_model(self):
        """Template model is the last fallback for model resolution."""
        body = _make_body(model=None)
        key = _make_key(default_model=None)
        tmpl = _make_template(model="google/gemini-flash-1.5")
        result = resolve_config(body, key, template=tmpl)
        assert result.model == "google/gemini-flash-1.5"

    def test_all_model_sources_absent_raises_422(self):
        """No model from any layer → UnprocessableEntityError."""
        body = _make_body(model=None)
        key = _make_key(default_model=None)
        with pytest.raises(UnprocessableEntityError):
            resolve_config(body, key)

    def test_body_model_overrides_template_model(self):
        """Body model beats template model even when template is present."""
        body = _make_body(model="openai/gpt-4o-mini")
        key = _make_key(default_model=None)
        tmpl = _make_template(model="google/gemini-flash-1.5")
        result = resolve_config(body, key, template=tmpl)
        assert result.model == "openai/gpt-4o-mini"


class TestInferenceParamPriority:

    def test_body_temperature_overrides_key_default(self):
        """temperature in body beats key.default_params."""
        body = _make_body(model="openai/gpt-4o", temperature=0.9)
        key = _make_key(default_model=None, default_params={"temperature": 0.1})
        result = resolve_config(body, key)
        assert result.temperature == 0.9

    def test_key_default_temperature_used_when_body_is_none(self):
        """Key default fills temperature when body omits it."""
        body = _make_body(model="openai/gpt-4o", temperature=None)
        key = _make_key(default_params={"temperature": 0.3})
        result = resolve_config(body, key)
        assert result.temperature == 0.3

    def test_template_param_used_when_body_and_key_both_none(self):
        """Template param is the lowest-priority fallback for inference params."""
        body = _make_body(model="openai/gpt-4o", temperature=None, max_tokens=None)
        key = _make_key(default_params={})
        tmpl = _make_template(params={"temperature": 0.7, "max_tokens": 512})
        result = resolve_config(body, key, template=tmpl)
        assert result.temperature == 0.7
        assert result.max_tokens == 512

    def test_key_param_beats_template_param(self):
        """Key default takes priority over template param for inference params."""
        body = _make_body(model="openai/gpt-4o", temperature=None)
        key = _make_key(default_params={"temperature": 0.5})
        tmpl = _make_template(params={"temperature": 0.9})
        result = resolve_config(body, key, template=tmpl)
        assert result.temperature == 0.5

    def test_all_mergeable_params_resolved(self):
        """All _MERGEABLE_PARAMS are filled from key defaults."""
        body = _make_body(model="openai/gpt-4o")
        key = _make_key(default_params={
            "temperature": 0.5,
            "max_tokens": 256,
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.2,
            "stop": ["\n"],
            "seed": 42,
        })
        result = resolve_config(body, key)
        assert result.temperature == 0.5
        assert result.max_tokens == 256
        assert result.top_p == 0.9
        assert result.frequency_penalty == 0.1
        assert result.presence_penalty == 0.2
        assert result.stop == ["\n"]
        assert result.seed == 42


class TestMessageAssembly:

    def test_rendered_messages_prepended_before_body_messages(self):
        """Template base messages come before the caller's messages."""
        rendered = [{"role": "system", "content": "You are a bot."}]
        body = _make_body(
            model="openai/gpt-4o",
            messages=[Message(role="user", content="hi")]
        )
        key = _make_key()
        result = resolve_config(body, key, rendered_messages=rendered)
        assert result.messages[0].role == "system"
        assert result.messages[0].content == "You are a bot."
        assert result.messages[1].role == "user"
        assert result.messages[1].content == "hi"

    def test_no_template_body_messages_unchanged(self):
        """Without rendered messages, body.messages are passed through unchanged."""
        msgs = [Message(role="user", content="ping")]
        body = _make_body(model="openai/gpt-4o", messages=msgs)
        key = _make_key()
        result = resolve_config(body, key)
        assert len(result.messages) == 1
        assert result.messages[0].content == "ping"

    def test_multiple_rendered_messages_all_prepended(self):
        """Multiple rendered messages are prepended in order."""
        rendered = [
            {"role": "system", "content": "Sys"},
            {"role": "user", "content": "Base user"},
            {"role": "assistant", "content": "Base assistant"},
        ]
        body = _make_body(
            model="openai/gpt-4o",
            messages=[Message(role="user", content="Real question")]
        )
        key = _make_key()
        result = resolve_config(body, key, rendered_messages=rendered)
        assert len(result.messages) == 4
        assert result.messages[3].content == "Real question"


class TestStructuralFieldsNotMerged:

    def test_tools_not_pulled_from_key_defaults(self):
        """tools is structural — never inherited from key.default_params."""
        body = _make_body(model="openai/gpt-4o", tools=None)
        key = _make_key(default_params={"tools": [{"type": "function"}]})
        result = resolve_config(body, key)
        assert result.tools is None

    def test_stream_not_overridden_by_key_defaults(self):
        """stream flag in body is not overridden by key defaults."""
        body = _make_body(model="openai/gpt-4o")
        key = _make_key(default_params={"stream": True})
        result = resolve_config(body, key)
        # stream defaults to False in ChatCompletionRequest and is not in _MERGEABLE_PARAMS
        assert result.stream is False


class TestReturnType:

    def test_returns_chat_completion_request(self):
        """resolve_config always returns a ChatCompletionRequest instance."""
        body = _make_body(model="openai/gpt-4o")
        key = _make_key()
        result = resolve_config(body, key)
        assert isinstance(result, ChatCompletionRequest)

    def test_routerv_only_fields_carried_through(self):
        """RouterV-only fields (template, variables, session_id) are preserved
        in the resolved config so _build_payload can strip them later."""
        body = _make_body(
            model="openai/gpt-4o",
            template="my-template",
            variables={"k": "v"},
            session_id="sess-001",
        )
        key = _make_key()
        result = resolve_config(body, key)
        assert result.template == "my-template"
        assert result.variables == {"k": "v"}
        assert result.session_id == "sess-001"
