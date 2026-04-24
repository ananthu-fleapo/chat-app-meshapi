"""
Unit tests for app/auto_router/service.py

Covers:
  _is_auto               — "auto", case variants, non-auto values
  _inject_auto_route_meta — response body fields set correctly
  _auto_route_headers     — streaming header dict
  resolve_auto_model      — happy path, empty registry, timeout, invalid response
  _use_fallback           — misconfigured (empty fallback, fallback not in registry)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── _is_auto ──────────────────────────────────────────────────────────────────

class TestIsAuto:

    def test_lowercase_auto_is_true(self):
        from app.auto_router.service import _is_auto
        assert _is_auto("auto") is True

    def test_uppercase_auto_is_true(self):
        from app.auto_router.service import _is_auto
        assert _is_auto("AUTO") is True

    def test_mixed_case_auto_is_true(self):
        from app.auto_router.service import _is_auto
        assert _is_auto("Auto") is True

    def test_whitespace_padded_auto_is_true(self):
        from app.auto_router.service import _is_auto
        assert _is_auto("  auto  ") is True

    def test_concrete_model_is_false(self):
        from app.auto_router.service import _is_auto
        assert _is_auto("openai/gpt-4o") is False

    def test_empty_string_is_false(self):
        from app.auto_router.service import _is_auto
        assert _is_auto("") is False

    def test_none_is_false(self):
        from app.auto_router.service import _is_auto
        assert _is_auto(None) is False

    def test_partial_match_is_false(self):
        from app.auto_router.service import _is_auto
        assert _is_auto("autorouter") is False


# ── _inject_auto_route_meta ───────────────────────────────────────────────────

class TestInjectAutoRouteMeta:

    def test_non_fallback_sets_auto_routed_and_model_id(self):
        from app.auto_router.service import AutoRouteResult, _inject_auto_route_meta

        body: dict = {}
        result = AutoRouteResult(resolved_model_id="openai/gpt-4o")
        _inject_auto_route_meta(body, result)

        assert body["x_auto_routed"] is True
        assert body["x_resolved_model_id"] == "openai/gpt-4o"
        assert "x_auto_routed_fallback" not in body

    def test_fallback_sets_fallback_fields(self):
        from app.auto_router.service import AutoRouteResult, _inject_auto_route_meta

        body: dict = {}
        result = AutoRouteResult(
            resolved_model_id="openai/gpt-4o-mini",
            used_fallback=True,
            fallback_reason="classifier_timeout",
        )
        _inject_auto_route_meta(body, result)

        assert body["x_auto_routed"] is True
        assert body["x_auto_routed_fallback"] is True
        assert body["x_auto_routed_fallback_reason"] == "classifier_timeout"


# ── _auto_route_headers ───────────────────────────────────────────────────────

class TestAutoRouteHeaders:

    def test_non_fallback_returns_two_headers(self):
        from app.auto_router.service import AutoRouteResult, _auto_route_headers

        result = AutoRouteResult(resolved_model_id="openai/gpt-4o")
        headers = _auto_route_headers(result)

        assert headers["X-Auto-Routed"] == "true"
        assert headers["X-Resolved-Model-Id"] == "openai/gpt-4o"
        assert "X-Auto-Routed-Fallback" not in headers

    def test_fallback_includes_fallback_headers(self):
        from app.auto_router.service import AutoRouteResult, _auto_route_headers

        result = AutoRouteResult(
            resolved_model_id="openai/gpt-4o-mini",
            used_fallback=True,
            fallback_reason="empty_registry",
        )
        headers = _auto_route_headers(result)

        assert headers["X-Auto-Routed-Fallback"] == "true"
        assert headers["X-Auto-Routed-Fallback-Reason"] == "empty_registry"

    def test_fallback_reason_none_becomes_empty_string(self):
        from app.auto_router.service import AutoRouteResult, _auto_route_headers

        result = AutoRouteResult(
            resolved_model_id="openai/gpt-4o-mini",
            used_fallback=True,
            fallback_reason=None,
        )
        headers = _auto_route_headers(result)

        assert headers["X-Auto-Routed-Fallback-Reason"] == ""


# ── resolve_auto_model ────────────────────────────────────────────────────────

class TestResolveAutoModel:

    async def test_happy_path_returns_classifier_model(self):
        from app.auto_router.service import resolve_auto_model

        candidates = [MagicMock(model_id="openai/gpt-4o")]

        with (
            patch("app.auto_router.service.get_enabled_models", AsyncMock(return_value=candidates)),
            patch("app.auto_router.service.call_classifier", AsyncMock(return_value=("openai/gpt-4o", "", {"model_id": "openai/gpt-4o-mini", "provider": "openrouter", "prompt_tokens": 120, "completion_tokens": 3, "cost": 0.000005}))),
            patch("app.auto_router.service.parse_classifier_response", return_value="openai/gpt-4o"),
            patch("app.auto_router.service.AUTO_ROUTER_REQUESTS"),
            patch("app.auto_router.service.AUTO_ROUTER_CLASSIFIER_LATENCY"),
            patch("app.auto_router.service.settings") as mock_settings,
        ):
            mock_settings.auto_router_use_benchmarks = False
            result = await resolve_auto_model("Translate this text", "completions", db=AsyncMock(), owner="test-owner")

        assert result.resolved_model_id == "openai/gpt-4o"
        assert result.used_fallback is False
        assert result.fallback_reason is None

    async def test_empty_registry_skips_classifiers_and_uses_default(self):
        from app.auto_router.service import resolve_auto_model

        with (
            patch("app.auto_router.service.get_enabled_models", AsyncMock(return_value=[])),
            patch("app.auto_router.service.AUTO_ROUTER_REQUESTS"),
            patch("app.auto_router.service.AUTO_ROUTER_FALLBACK") as mock_fallback_ctr,
            patch("app.auto_router.service.settings") as mock_settings,
        ):
            mock_settings.auto_router_use_benchmarks = False
            mock_settings.auto_router_fallback_model_id = "openai/gpt-4o-mini"
            mock_settings.auto_router_default_model_id = "openai/gpt-4o-mini"
            mock_fallback_ctr.labels.return_value = MagicMock()
            result = await resolve_auto_model("Hello", "completions", db=AsyncMock(), owner="test-owner")

        assert result.used_fallback is True
        assert result.fallback_reason == "empty_registry"
        assert result.resolved_model_id == "openai/gpt-4o-mini"

    async def test_primary_timeout_retries_with_fallback_classifier(self):
        """Primary times out → fallback classifier called → returns valid model."""
        from app.auto_router.service import resolve_auto_model

        candidates = [MagicMock(model_id="openai/gpt-4o")]
        call_count = 0

        async def mock_classifier(*args, classifier_model_id=None, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (None, "classifier_timeout", None)  # primary fails
            return ("openai/gpt-4o", "", None)              # fallback succeeds

        with (
            patch("app.auto_router.service.get_enabled_models", AsyncMock(return_value=candidates)),
            patch("app.auto_router.service.call_classifier", side_effect=mock_classifier),
            patch("app.auto_router.service.parse_classifier_response", side_effect=[None, "openai/gpt-4o"]),
            patch("app.auto_router.service.AUTO_ROUTER_REQUESTS"),
            patch("app.auto_router.service.AUTO_ROUTER_CLASSIFIER_LATENCY"),
            patch("app.auto_router.service.settings") as mock_settings,
        ):
            mock_settings.auto_router_use_benchmarks = False
            mock_settings.auto_router_fallback_model_id = "openai/gpt-4o-mini"
            mock_settings.auto_router_default_model_id = "openai/gpt-4o-mini"
            result = await resolve_auto_model("Hello", "completions", db=AsyncMock(), owner="test-owner")

        assert result.used_fallback is False
        assert result.resolved_model_id == "openai/gpt-4o"
        assert call_count == 2

    async def test_both_classifiers_fail_uses_default_model(self):
        """Both primary and fallback classifiers fail → default model used."""
        from app.auto_router.service import resolve_auto_model

        candidates = [MagicMock(model_id="openai/gpt-4o")]

        with (
            patch("app.auto_router.service.get_enabled_models", AsyncMock(return_value=candidates)),
            patch("app.auto_router.service.call_classifier", AsyncMock(return_value=(None, "classifier_timeout", None))),
            patch("app.auto_router.service.parse_classifier_response", return_value=None),
            patch("app.auto_router.service.AUTO_ROUTER_REQUESTS"),
            patch("app.auto_router.service.AUTO_ROUTER_CLASSIFIER_LATENCY"),
            patch("app.auto_router.service.AUTO_ROUTER_FALLBACK") as mock_fallback_ctr,
            patch("app.auto_router.service.settings") as mock_settings,
        ):
            mock_settings.auto_router_use_benchmarks = False
            mock_settings.auto_router_fallback_model_id = "openai/gpt-4o-mini"
            mock_settings.auto_router_default_model_id = "openai/gpt-4o"
            mock_fallback_ctr.labels.return_value = MagicMock()
            result = await resolve_auto_model("Hello", "completions", db=AsyncMock(), owner="test-owner")

        assert result.used_fallback is True
        assert result.fallback_reason == "classifier_timeout"
        assert result.resolved_model_id == "openai/gpt-4o"

    async def test_invalid_classifier_response_retries_fallback_classifier(self):
        """Primary returns unrecognised ID → fallback classifier called."""
        from app.auto_router.service import resolve_auto_model

        candidates = [MagicMock(model_id="openai/gpt-4o")]
        call_count = 0

        async def mock_classifier(*args, classifier_model_id=None, **kwargs):
            nonlocal call_count
            call_count += 1
            return ("not-real", "", None)

        with (
            patch("app.auto_router.service.get_enabled_models", AsyncMock(return_value=candidates)),
            patch("app.auto_router.service.call_classifier", side_effect=mock_classifier),
            patch("app.auto_router.service.parse_classifier_response", return_value=None),
            patch("app.auto_router.service.AUTO_ROUTER_REQUESTS"),
            patch("app.auto_router.service.AUTO_ROUTER_CLASSIFIER_LATENCY"),
            patch("app.auto_router.service.AUTO_ROUTER_FALLBACK") as mock_fallback_ctr,
            patch("app.auto_router.service.settings") as mock_settings,
        ):
            mock_settings.auto_router_use_benchmarks = False
            mock_settings.auto_router_fallback_model_id = "openai/gpt-4o-mini"
            mock_settings.auto_router_default_model_id = "openai/gpt-4o"
            mock_fallback_ctr.labels.return_value = MagicMock()
            result = await resolve_auto_model("Hello", "completions", db=AsyncMock(), owner="test-owner")

        assert result.used_fallback is True
        assert result.fallback_reason == "invalid_response"
        assert call_count == 2  # both classifiers were attempted

    async def test_no_fallback_classifier_configured_skips_retry(self):
        """When auto_router_fallback_model_id is empty, retry is skipped entirely."""
        from app.auto_router.service import resolve_auto_model

        candidates = [MagicMock(model_id="openai/gpt-4o")]
        call_count = 0

        async def mock_classifier(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return (None, "classifier_timeout", None)

        with (
            patch("app.auto_router.service.get_enabled_models", AsyncMock(return_value=candidates)),
            patch("app.auto_router.service.call_classifier", side_effect=mock_classifier),
            patch("app.auto_router.service.parse_classifier_response", return_value=None),
            patch("app.auto_router.service.AUTO_ROUTER_REQUESTS"),
            patch("app.auto_router.service.AUTO_ROUTER_CLASSIFIER_LATENCY"),
            patch("app.auto_router.service.AUTO_ROUTER_FALLBACK") as mock_fallback_ctr,
            patch("app.auto_router.service.settings") as mock_settings,
        ):
            mock_settings.auto_router_use_benchmarks = False
            mock_settings.auto_router_fallback_model_id = ""
            mock_settings.auto_router_default_model_id = "openai/gpt-4o"
            mock_fallback_ctr.labels.return_value = MagicMock()
            result = await resolve_auto_model("Hello", "completions", db=AsyncMock(), owner="test-owner")

        assert call_count == 1  # only primary called
        assert result.used_fallback is True

    async def test_counter_incremented_on_every_call(self):
        from app.auto_router.service import resolve_auto_model

        candidates = [MagicMock(model_id="m")]

        with (
            patch("app.auto_router.service.get_enabled_models", AsyncMock(return_value=candidates)),
            patch("app.auto_router.service.call_classifier", AsyncMock(return_value=("m", "", None))),
            patch("app.auto_router.service.parse_classifier_response", return_value="m"),
            patch("app.auto_router.service.AUTO_ROUTER_REQUESTS") as mock_counter,
            patch("app.auto_router.service.AUTO_ROUTER_CLASSIFIER_LATENCY"),
            patch("app.auto_router.service.settings") as mock_settings,
        ):
            mock_settings.auto_router_use_benchmarks = False
            await resolve_auto_model("test", "completions", db=AsyncMock(), owner="test-owner")

        mock_counter.inc.assert_called_once()


# ── _use_default ──────────────────────────────────────────────────────────────

class TestUseDefault:

    def test_empty_default_raises_misconfigured_error(self):
        from app.auto_router.service import _use_default
        from app.exceptions import AutoRouterMisconfiguredError

        with patch("app.auto_router.service.settings") as mock_settings:
            mock_settings.auto_router_default_model_id = ""
            with pytest.raises(AutoRouterMisconfiguredError):
                _use_default("classifier_timeout", {"openai/gpt-4o"}, "req_1")

    def test_whitespace_only_default_raises_misconfigured_error(self):
        from app.auto_router.service import _use_default
        from app.exceptions import AutoRouterMisconfiguredError

        with patch("app.auto_router.service.settings") as mock_settings:
            mock_settings.auto_router_default_model_id = "   "
            with pytest.raises(AutoRouterMisconfiguredError):
                _use_default("classifier_timeout", {"openai/gpt-4o"}, "req_1")

    def test_default_not_in_registry_raises_misconfigured_error(self):
        from app.auto_router.service import _use_default
        from app.exceptions import AutoRouterMisconfiguredError

        with patch("app.auto_router.service.settings") as mock_settings:
            mock_settings.auto_router_default_model_id = "openai/gpt-4o-mini"
            with pytest.raises(AutoRouterMisconfiguredError):
                _use_default("classifier_timeout", {"openai/gpt-4o"}, "req_1")

    def test_default_in_registry_returns_result(self):
        from app.auto_router.service import _use_default

        with patch("app.auto_router.service.settings") as mock_settings:
            mock_settings.auto_router_default_model_id = "openai/gpt-4o-mini"
            result = _use_default("classifier_error", {"openai/gpt-4o", "openai/gpt-4o-mini"}, "req_1")

        assert result.resolved_model_id == "openai/gpt-4o-mini"
        assert result.used_fallback is True
        assert result.fallback_reason == "classifier_error"

    def test_empty_registry_skips_membership_check(self):
        """When no candidates exist, default is used without requiring it be in the registry."""
        from app.auto_router.service import _use_default

        with patch("app.auto_router.service.settings") as mock_settings:
            mock_settings.auto_router_default_model_id = "openai/gpt-4o-mini"
            result = _use_default("empty_registry", set(), "req_1")

        assert result.resolved_model_id == "openai/gpt-4o-mini"
        assert result.used_fallback is True
