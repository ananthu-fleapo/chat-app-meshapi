"""
Integration tests for POST /v1/chat/compare.

Uses FastAPI TestClient with dependency overrides for auth and DB.
All upstream calls (fan_out_completions, run_comparison) are mocked at the
router import level so no real network or DB access is needed.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.compare import CompareResponse, ModelCompareResult, TokenUsage


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_key():
    key = MagicMock()
    key.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    key.owner = "acme"
    key.rpm_limit = None
    key.rpd_limit = None
    key.tpm_limit = None
    key.spend_cap_usd = None
    key.default_model = None
    key.default_params = None
    return key


def _result(model: str, content: str = "ok", error: str | None = None) -> ModelCompareResult:
    return ModelCompareResult(
        model=model,
        response_body=None,
        content=content if not error else None,
        latency_ms=100,
        error=error,
        error_code="upstream_error" if error else None,
        usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        request_id=f"req::{model}",
    )


def _base_body(**kwargs) -> dict:
    base = {
        "models": ["openai/gpt-4o-mini", "anthropic/claude-3-haiku"],
        "messages": [{"role": "user", "content": "Hello"}],
        "comparison_model": "openai/gpt-4o-mini",
    }
    base.update(kwargs)
    return base


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    execute_result.scalar_one.return_value = 0
    execute_result.scalars.return_value.all.return_value = []
    execute_result.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result)
    return session


@pytest.fixture
def client(mock_db_session):
    from app.auth.dependencies import get_authenticated_key
    from app.cache.redis_client import get_redis
    from app.db.session import get_db_session
    from app.main import create_app

    app = create_app()

    async def _override_db():
        yield mock_db_session

    async def _override_key():
        return _make_key()

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_authenticated_key] = _override_key
    app.dependency_overrides[get_redis] = lambda: None

    return TestClient(app, raise_server_exceptions=False)


# ── Non-streaming path ────────────────────────────────────────────────────────


class TestChatCompareNonStreaming:

    def test_two_models_success_returns_200_with_comparison(self, client):
        results = [_result("openai/gpt-4o-mini"), _result("anthropic/claude-3-haiku")]
        comparison_text = "Both are good. GPT-4o is slightly more concise."

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.check_balance", AsyncMock()),
            patch(
                "app.routers.compare.fan_out_completions",
                AsyncMock(return_value=results),
            ),
            patch(
                "app.routers.compare.run_comparison",
                AsyncMock(
                    return_value=(
                        comparison_text,
                        TokenUsage(prompt_tokens=50, completion_tokens=100, total_tokens=150),
                        "openai/gpt-4o-mini",
                        False,
                    )
                ),
            ),
        ):
            resp = client.post("/v1/chat/compare", json=_base_body())

        assert resp.status_code == 200
        body = resp.json()
        assert body["object"] == "compare.completion"
        assert body["comparison"] == comparison_text
        assert len(body["results"]) == 2
        assert body["partial"] is False

    def test_all_models_fail_returns_502(self, client):
        results = [
            _result("m1", error="timeout"),
            _result("m2", error="provider error"),
        ]

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.check_balance", AsyncMock()),
            patch(
                "app.routers.compare.fan_out_completions",
                AsyncMock(return_value=results),
            ),
        ):
            resp = client.post("/v1/chat/compare", json=_base_body(models=["m1", "m2"]))

        assert resp.status_code == 502
        body = resp.json()
        assert body["detail"]["error"]["code"] == "all_models_failed"
        assert len(body["detail"]["error"]["details"]) == 2

    def test_partial_failure_still_returns_200(self, client):
        results = [
            _result("good-model", content="great answer"),
            _result("bad-model", error="timeout"),
        ]

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.check_balance", AsyncMock()),
            patch(
                "app.routers.compare.fan_out_completions",
                AsyncMock(return_value=results),
            ),
            patch(
                "app.routers.compare.run_comparison",
                AsyncMock(return_value=("Only one model responded.", None, "openai/gpt-4o-mini", False)),
            ),
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(models=["good-model", "bad-model"]),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["partial"] is True

    def test_single_model_success_skips_comparison(self, client):
        results = [_result("solo-model")]

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.check_balance", AsyncMock()),
            patch(
                "app.routers.compare.fan_out_completions",
                AsyncMock(return_value=results),
            ),
            patch("app.routers.compare.run_comparison") as mock_comparison,
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(models=["solo-model"]),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["comparison"] is None
        mock_comparison.assert_not_called()

    def test_duplicate_models_deduplicated(self, client):
        captured: list = []

        async def capture_fan_out(*, request, **kwargs):
            captured.append(request.models)
            return [_result(m) for m in request.models]

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.check_balance", AsyncMock()),
            patch("app.routers.compare.fan_out_completions", side_effect=capture_fan_out),
            patch(
                "app.routers.compare.run_comparison",
                AsyncMock(return_value=("comparison", None, "openai/gpt-4o-mini", False)),
            ),
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(models=["a", "a", "b"]),
            )

        assert resp.status_code == 200
        assert captured[0] == ["a", "b"]

    def test_11_models_returns_422(self, client):
        resp = client.post(
            "/v1/chat/compare",
            json=_base_body(models=[f"model-{i}" for i in range(11)]),
        )
        assert resp.status_code == 422

    def test_no_comparison_model_no_default_returns_422(self, client):
        with patch("app.routers.compare.settings") as mock_settings:
            mock_settings.compare_default_model = ""
            mock_settings.compare_max_models = 10
            mock_settings.default_rpm = 60
            mock_settings.default_rpd = 5000
            mock_settings.max_rpm = 100
            mock_settings.max_rpd = 7500

            resp = client.post(
                "/v1/chat/compare",
                json={
                    "models": ["model-a", "model-b"],
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
        # Pydantic validation allows missing comparison_model (it's optional),
        # but the router should raise 422 when no default is configured either
        assert resp.status_code == 422

    def test_rate_limit_returns_429(self, client):
        from app.exceptions import RateLimitError

        with patch(
            "app.routers.compare.check_rate_limits",
            AsyncMock(side_effect=RateLimitError("RPM exceeded")),
        ):
            resp = client.post("/v1/chat/compare", json=_base_body())

        assert resp.status_code == 429

    def test_response_includes_x_request_id_header(self, client):
        results = [_result("m1"), _result("m2")]

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.check_balance", AsyncMock()),
            patch(
                "app.routers.compare.fan_out_completions",
                AsyncMock(return_value=results),
            ),
            patch(
                "app.routers.compare.run_comparison",
                AsyncMock(return_value=("comparison text", None, "openai/gpt-4o-mini", False)),
            ),
        ):
            resp = client.post("/v1/chat/compare", json=_base_body())

        assert resp.status_code == 200
        assert "x-request-id" in resp.headers


# ── Streaming path ────────────────────────────────────────────────────────────


class TestChatCompareStreaming:

    def _parse_sse_events(self, text: str) -> list[dict]:
        """Parse SSE response into list of {event, data} dicts."""
        events = []
        current: dict = {}
        for line in text.splitlines():
            if line.startswith("event: "):
                current["event"] = line[7:]
            elif line.startswith("data: "):
                try:
                    current["data"] = json.loads(line[6:])
                except json.JSONDecodeError:
                    current["data"] = line[6:]
            elif line == "" and current:
                events.append(current)
                current = {}
        return events

    def test_streaming_emits_required_event_types(self, client):
        results = [_result("m1"), _result("m2")]

        async def fake_stream(**kwargs):
            yield b"data: {}\n\n"

        adapter = MagicMock()
        adapter.stream_chat_completion = MagicMock(return_value=fake_stream())

        call_index = {"n": 0}

        async def mock_single_call(**kwargs):
            i = call_index["n"]
            call_index["n"] += 1
            return results[i] if i < len(results) else results[-1]

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.check_balance", AsyncMock()),
            patch("app.routers.compare._call_single_model", side_effect=mock_single_call),
            patch("app.routers.compare.resolve_routing", AsyncMock(return_value=("openrouter", "m", None))),
            patch("app.routers.compare.resolve_upstream_key", AsyncMock(return_value="sk")),
            patch("app.routers.compare.get_adapter", return_value=adapter),
            patch("app.routers.compare.build_comparison_messages", return_value=[
                {"role": "user", "content": "compare"}
            ]),
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(stream=True),
            )

        assert resp.status_code == 200
        events = self._parse_sse_events(resp.text)
        event_types = [e.get("event") for e in events]
        assert "meta" in event_types
        assert "done" in event_types

    def test_streaming_meta_contains_comparison_id(self, client):
        results = [_result("m1"), _result("m2")]

        async def fake_stream(**kwargs):
            return
            yield  # make it an async generator

        adapter = MagicMock()
        adapter.stream_chat_completion = MagicMock(return_value=fake_stream())

        import asyncio as _asyncio

        async def _fake_call(**kwargs):
            model = kwargs.get("model", "m1")
            return results[0] if model == "m1" else results[1]

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.check_balance", AsyncMock()),
            patch("app.routers.compare._call_single_model", side_effect=_fake_call),
            patch("app.routers.compare.resolve_routing", AsyncMock(return_value=("openrouter", "m", None))),
            patch("app.routers.compare.resolve_upstream_key", AsyncMock(return_value="sk")),
            patch("app.routers.compare.get_adapter", return_value=adapter),
            patch("app.routers.compare.build_comparison_messages", return_value=[]),
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(stream=True),
            )

        assert resp.status_code == 200
        events = self._parse_sse_events(resp.text)
        meta_events = [e for e in events if e.get("event") == "meta"]
        assert len(meta_events) >= 1
        assert "comparison_id" in meta_events[0].get("data", {})


# ── skip_comparison non-streaming ─────────────────────────────────────────────


class TestChatCompareSkipComparison:

    def test_skip_comparison_non_streaming_returns_no_comparison(self, client):
        results = [_result("m1"), _result("m2")]

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.fan_out_completions", AsyncMock(return_value=results)),
            patch("app.routers.compare.run_comparison") as mock_run,
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(skip_comparison=True),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["comparison"] is None
        assert body["skip_comparison"] is True
        mock_run.assert_not_called()

    def test_skip_comparison_skips_balance_check(self, client):
        results = [_result("m1"), _result("m2")]

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.check_balance") as mock_balance,
            patch("app.routers.compare.fan_out_completions", AsyncMock(return_value=results)),
            patch("app.routers.compare.run_comparison", AsyncMock(return_value=(None, None, None, False))),
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(skip_comparison=True),
            )

        assert resp.status_code == 200
        mock_balance.assert_not_called()

    def test_skip_comparison_no_comparison_model_required(self, client):
        results = [_result("m1"), _result("m2")]

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare.settings") as mock_settings,
            patch("app.routers.compare.fan_out_completions", AsyncMock(return_value=results)),
        ):
            mock_settings.compare_default_model = ""
            mock_settings.compare_max_models = 10
            mock_settings.default_rpm = 60
            mock_settings.default_rpd = 5000
            mock_settings.max_rpm = 100
            mock_settings.max_rpd = 7500

            resp = client.post(
                "/v1/chat/compare",
                json={
                    "models": ["m1", "m2"],
                    "messages": [{"role": "user", "content": "hi"}],
                    "skip_comparison": True,
                },
            )

        assert resp.status_code == 200


# ── skip_comparison streaming ──────────────────────────────────────────────────


class TestChatCompareSkipComparisonStreaming:

    def _parse_sse_events(self, text: str) -> list[dict]:
        events = []
        current: dict = {}
        for line in text.splitlines():
            if line.startswith("event: "):
                current["event"] = line[7:]
            elif line.startswith("data: "):
                try:
                    current["data"] = json.loads(line[6:])
                except json.JSONDecodeError:
                    current["data"] = line[6:]
            elif line == "" and current:
                events.append(current)
                current = {}
        return events

    def test_skip_comparison_streaming_emits_model_chunk_and_done(self, client):
        async def fake_queue_filler(*, model, queue, **kwargs):
            await queue.put((model, {"delta": "chunk", "finish_reason": None, "usage": None}, None))
            await queue.put((model, None, None))

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare._stream_single_model_into_queue", side_effect=fake_queue_filler),
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(models=["m1"], stream=True, skip_comparison=True),
            )

        assert resp.status_code == 200
        events = self._parse_sse_events(resp.text)
        event_types = [e.get("event") for e in events]
        assert "meta" in event_types
        assert "model_chunk" in event_types
        assert "model_stream_done" in event_types
        assert "done" in event_types

    def test_skip_comparison_streaming_model_chunk_has_model_and_delta(self, client):
        async def fake_queue_filler(*, model, queue, **kwargs):
            await queue.put((model, {"delta": "hello", "finish_reason": None, "usage": None}, None))
            await queue.put((model, None, None))

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare._stream_single_model_into_queue", side_effect=fake_queue_filler),
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(models=["solo-model"], stream=True, skip_comparison=True),
            )

        events = self._parse_sse_events(resp.text)
        chunk_events = [e for e in events if e.get("event") == "model_chunk"]
        assert len(chunk_events) >= 1
        assert chunk_events[0]["data"]["model"] == "solo-model"
        assert "delta" in chunk_events[0]["data"]
        assert chunk_events[0]["data"]["delta"] == "hello"

    def test_skip_comparison_streaming_meta_has_skip_comparison_flag(self, client):
        async def fake_queue_filler(*, model, queue, **kwargs):
            await queue.put((model, None, None))

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare._stream_single_model_into_queue", side_effect=fake_queue_filler),
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(models=["m1"], stream=True, skip_comparison=True),
            )

        events = self._parse_sse_events(resp.text)
        meta = next(e for e in events if e.get("event") == "meta")
        assert meta["data"]["skip_comparison"] is True
        assert meta["data"]["comparison_model"] is None

    def test_skip_comparison_streaming_no_comparison_chunk_emitted(self, client):
        async def fake_queue_filler(*, model, queue, **kwargs):
            await queue.put((model, None, None))

        with (
            patch("app.routers.compare.check_rate_limits", AsyncMock()),
            patch("app.routers.compare.check_tpm_limit", AsyncMock()),
            patch("app.routers.compare.check_spend_cap", AsyncMock()),
            patch("app.routers.compare._stream_single_model_into_queue", side_effect=fake_queue_filler),
        ):
            resp = client.post(
                "/v1/chat/compare",
                json=_base_body(models=["m1"], stream=True, skip_comparison=True),
            )

        events = self._parse_sse_events(resp.text)
        assert not any(e.get("event") == "comparison_chunk" for e in events)
