"""
Unit tests for app/auto_router/classifier.py

Covers:
  parse_classifier_response — valid ID, whitespace stripping, first-line only,
                               None/empty input, unknown ID → None
  call_classifier           — success path, timeout, adapter exception
  _build_user_message       — prompt structure with candidates and user content
"""

import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auto_router.registry import CandidateModel


def _make_candidate(model_id: str, name: str = "", description: str = "") -> CandidateModel:
    return CandidateModel(model_id=model_id, name=name or model_id, description=description)


# ── parse_classifier_response ─────────────────────────────────────────────────

class TestParseClassifierResponse:

    def test_valid_id_returned_unchanged(self):
        from app.auto_router.classifier import parse_classifier_response

        result = parse_classifier_response("openai/gpt-4o", {"openai/gpt-4o", "anthropic/claude-3-5"})
        assert result == "openai/gpt-4o"

    def test_strips_surrounding_whitespace(self):
        from app.auto_router.classifier import parse_classifier_response

        result = parse_classifier_response("  openai/gpt-4o  ", {"openai/gpt-4o"})
        assert result == "openai/gpt-4o"

    def test_takes_first_line_only(self):
        from app.auto_router.classifier import parse_classifier_response

        raw = "openai/gpt-4o\nThis model is best because...\nSome explanation."
        result = parse_classifier_response(raw, {"openai/gpt-4o"})
        assert result == "openai/gpt-4o"

    def test_none_returns_none(self):
        from app.auto_router.classifier import parse_classifier_response

        assert parse_classifier_response(None, {"openai/gpt-4o"}) is None

    def test_empty_string_returns_none(self):
        from app.auto_router.classifier import parse_classifier_response

        assert parse_classifier_response("", {"openai/gpt-4o"}) is None

    def test_whitespace_only_returns_none(self):
        from app.auto_router.classifier import parse_classifier_response

        assert parse_classifier_response("   \n  ", {"openai/gpt-4o"}) is None

    def test_unknown_id_returns_none(self):
        from app.auto_router.classifier import parse_classifier_response

        result = parse_classifier_response("unknown/model", {"openai/gpt-4o", "anthropic/claude-3-5"})
        assert result is None

    def test_quoted_id_returns_none(self):
        from app.auto_router.classifier import parse_classifier_response

        # Classifier wrapped the ID in quotes — should fail membership check
        result = parse_classifier_response('"openai/gpt-4o"', {"openai/gpt-4o"})
        assert result is None

    def test_empty_valid_ids_returns_none(self):
        from app.auto_router.classifier import parse_classifier_response

        result = parse_classifier_response("openai/gpt-4o", set())
        assert result is None


# ── _build_user_message ───────────────────────────────────────────────────────

class TestBuildUserMessage:

    def test_contains_all_candidate_ids(self):
        from app.auto_router.classifier import _build_user_message

        candidates = [
            _make_candidate("openai/gpt-4o", "GPT-4o", "Powerful"),
            _make_candidate("openai/gpt-4o-mini", "GPT-4o Mini", "Fast and cheap"),
        ]
        msg = _build_user_message(candidates, "Hello")
        assert "openai/gpt-4o" in msg
        assert "openai/gpt-4o-mini" in msg

    def test_contains_user_content(self):
        from app.auto_router.classifier import _build_user_message

        candidates = [_make_candidate("m")]
        msg = _build_user_message(candidates, "Summarize this document")
        assert "Summarize this document" in msg

    def test_user_content_truncated_to_2000_chars(self):
        from app.auto_router.classifier import _build_user_message

        candidates = [_make_candidate("m")]
        long_content = "X" * 5000
        msg = _build_user_message(candidates, long_content)
        assert "X" * 2000 in msg
        assert "X" * 2001 not in msg

    def test_empty_description_uses_general_purpose(self):
        from app.auto_router.classifier import _build_user_message

        candidates = [_make_candidate("m", description="")]
        msg = _build_user_message(candidates, "test")
        assert "General purpose" in msg

    def test_description_included_when_present(self):
        from app.auto_router.classifier import _build_user_message

        candidates = [_make_candidate("m", description="Code generation expert")]
        msg = _build_user_message(candidates, "Write a Python function")
        assert "Code generation expert" in msg


# ── call_classifier ───────────────────────────────────────────────────────────

@contextmanager
def _classifier_patches(mock_adapter, *, api_key="sys-key", provider="openrouter", provider_model_id="gpt-4o"):
    """Context manager that applies the three patches needed for every call_classifier test."""
    with (
        patch("app.providers.registry.resolve_routing", AsyncMock(return_value=(provider, provider_model_id, None))),
        patch("app.providers.key_resolver.resolve_upstream_key", AsyncMock(return_value=api_key)),
        patch("app.providers.registry.get_adapter", return_value=mock_adapter),
    ):
        yield


class TestCallClassifier:

    async def test_success_returns_content_and_empty_reason(self):
        from app.auto_router.classifier import call_classifier

        mock_response = {"choices": [{"message": {"content": "openai/gpt-4o"}}]}
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=mock_response)
        mock_db = AsyncMock()

        with _classifier_patches(mock_adapter):
            candidates = [_make_candidate("openai/gpt-4o")]
            content, reason, usage = await call_classifier(candidates, "Hello", db=mock_db, request_id="req_123", owner="test-owner")

        assert content == "openai/gpt-4o"
        assert reason == ""
        assert usage is not None
        assert "model_id" in usage
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage

    async def test_timeout_returns_none_and_classifier_timeout(self):
        from app.auto_router.classifier import call_classifier

        mock_adapter = MagicMock()
        mock_adapter.chat_completion = MagicMock(return_value=None)
        mock_db = AsyncMock()

        with _classifier_patches(mock_adapter):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                candidates = [_make_candidate("openai/gpt-4o")]
                content, reason, usage = await call_classifier(candidates, "Hello", db=mock_db, owner="test-owner")

        assert content is None
        assert reason == "classifier_timeout"
        assert usage is None

    async def test_adapter_exception_returns_none_and_classifier_error(self):
        from app.auto_router.classifier import call_classifier

        async def _raise(*args, **kwargs):
            raise RuntimeError("upstream down")

        mock_adapter = MagicMock()
        mock_adapter.chat_completion = _raise
        mock_db = AsyncMock()

        with _classifier_patches(mock_adapter):
            candidates = [_make_candidate("openai/gpt-4o")]
            content, reason, usage = await call_classifier(candidates, "Hello", db=mock_db, owner="test-owner")

        assert content is None
        assert reason == "classifier_error"
        assert usage is None

    async def test_empty_choices_returns_none_and_classifier_error(self):
        from app.auto_router.classifier import call_classifier

        mock_response = {"choices": []}
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=mock_response)
        mock_db = AsyncMock()

        with _classifier_patches(mock_adapter):
            candidates = [_make_candidate("openai/gpt-4o")]
            content, reason, usage = await call_classifier(candidates, "Hello", db=mock_db, owner="test-owner")

        assert content is None
        assert reason == "classifier_error"
        assert usage is None

    async def test_uses_resolved_provider_key_not_hardcoded(self):
        """Verifies the key from resolve_upstream_key is passed to the adapter, not a hardcoded key."""
        from app.auto_router.classifier import call_classifier

        mock_response = {"choices": [{"message": {"content": "vertex/gemini-pro"}}]}
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=mock_response)
        mock_db = AsyncMock()

        with _classifier_patches(mock_adapter, api_key="vertex-sa-json", provider="vertex", provider_model_id="gemini-pro"):
            await call_classifier([_make_candidate("vertex/gemini-pro")], "test", db=mock_db, owner="test-owner")

        call_kwargs = mock_adapter.chat_completion.call_args
        assert call_kwargs.kwargs["api_key"] == "vertex-sa-json"
        assert call_kwargs.kwargs["owner"] is None
        assert call_kwargs.kwargs["provider_model_id"] == "gemini-pro"

    async def test_resolve_routing_called_with_classifier_model_id(self):
        """Verifies the classifier model ID from settings is looked up, not a request model."""
        from app.auto_router.classifier import call_classifier
        from app.config import settings

        mock_response = {"choices": [{"message": {"content": "m"}}]}
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=mock_response)
        mock_db = AsyncMock()

        mock_resolve = AsyncMock(return_value=("openrouter", "m", None))
        with (
            patch("app.providers.registry.resolve_routing", mock_resolve),
            patch("app.providers.key_resolver.resolve_upstream_key", AsyncMock(return_value="k")),
            patch("app.providers.registry.get_adapter", return_value=mock_adapter),
        ):
            await call_classifier([_make_candidate("m")], "test", db=mock_db, owner="test-owner")

        mock_resolve.assert_awaited_once_with(settings.auto_router_classifier_model_id, mock_db)
