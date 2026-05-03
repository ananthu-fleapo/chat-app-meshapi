"""
Unit tests for app/compare/engine.py.

All upstream calls are mocked so no network or DB access is required.
"""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import Message
from app.schemas.compare import CompareRequest, ModelCompareResult, TokenUsage


def _key(owner: str = "test-owner") -> MagicMock:
    key = MagicMock()
    key.id = uuid.uuid4()
    key.owner = owner
    key.rpm_limit = None
    key.rpd_limit = None
    key.tpm_limit = None
    key.spend_cap_usd = None
    return key


def _mock_adapter(content: str = "response text") -> MagicMock:
    adapter = MagicMock()
    adapter.chat_completion = AsyncMock(return_value={
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    })
    return adapter


def _base_request(models: list[str]) -> CompareRequest:
    return CompareRequest(
        models=models,
        messages=[Message(role="user", content="Hello")],
    )


# ── fan_out_completions ───────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_upstream_key", new_callable=AsyncMock)
@patch("app.compare.engine.get_adapter")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_fan_out_all_success(
    mock_routing, mock_get_adapter, mock_upstream_key, mock_fire_log
):
    mock_routing.return_value = ("openrouter", "model-a", None)
    mock_upstream_key.return_value = "sk-test"
    mock_get_adapter.return_value = _mock_adapter()

    db = AsyncMock()
    key = _key()
    request = _base_request(["model-a", "model-b"])

    from app.compare.engine import fan_out_completions

    results = await fan_out_completions(
        request=request,
        key=key,
        db=db,
        outer_request_id="req_001",
        comparison_id="cmp_001",
    )

    assert len(results) == 2
    assert all(r.error is None for r in results)
    assert all(r.content == "response text" for r in results)
    assert mock_fire_log.call_count == 2


@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_upstream_key", new_callable=AsyncMock)
@patch("app.compare.engine.get_adapter")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_fan_out_one_failure(
    mock_routing, mock_get_adapter, mock_upstream_key, mock_fire_log
):
    adapter_ok = _mock_adapter("good response")
    adapter_fail = MagicMock()
    adapter_fail.chat_completion = AsyncMock(side_effect=Exception("upstream 500"))

    call_count = {"n": 0}

    def routing_side_effect(model, db):
        return ("openrouter", model, None)

    def adapter_side_effect(provider):
        call_count["n"] += 1
        return adapter_fail if call_count["n"] == 1 else adapter_ok

    mock_routing.side_effect = routing_side_effect
    mock_upstream_key.return_value = "sk-test"
    mock_get_adapter.side_effect = adapter_side_effect

    db = AsyncMock()
    key = _key()
    request = _base_request(["bad-model", "good-model"])

    from app.compare.engine import fan_out_completions

    results = await fan_out_completions(
        request=request,
        key=key,
        db=db,
        outer_request_id="req_002",
        comparison_id="cmp_002",
    )

    errors = [r for r in results if r.error is not None]
    successes = [r for r in results if r.error is None]
    assert len(errors) == 1
    assert len(successes) == 1
    assert errors[0].error_code == "upstream_error"


@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_fan_out_timeout_captured(mock_routing, mock_fire_log):
    async def slow_completion(*args, **kwargs):
        await asyncio.sleep(9999)

    adapter = MagicMock()
    adapter.chat_completion = slow_completion

    mock_routing.return_value = ("openrouter", "slow-model", None)

    with (
        patch("app.compare.engine.resolve_upstream_key", new_callable=AsyncMock, return_value="sk"),
        patch("app.compare.engine.get_adapter", return_value=adapter),
        patch("app.compare.engine.settings") as mock_settings,
    ):
        mock_settings.compare_model_timeout_s = 0.01

        from app.compare.engine import fan_out_completions

        request = _base_request(["slow-model"])
        results = await fan_out_completions(
            request=request,
            key=_key(),
            db=AsyncMock(),
            outer_request_id="req_003",
            comparison_id="cmp_003",
        )

    assert len(results) == 1
    assert results[0].error_code == "gateway_timeout"
    assert results[0].error is not None


@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_fan_out_unsupported_model(mock_routing, mock_fire_log):
    from app.exceptions import UnsupportedModelError

    mock_routing.side_effect = UnsupportedModelError("ghost-model")

    from app.compare.engine import fan_out_completions

    request = _base_request(["ghost-model"])
    results = await fan_out_completions(
        request=request,
        key=_key(),
        db=AsyncMock(),
        outer_request_id="req_004",
        comparison_id="cmp_004",
    )

    assert len(results) == 1
    assert results[0].error_code == "model_not_found"


@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_fan_out_all_fail(mock_routing, mock_fire_log):
    mock_routing.side_effect = Exception("provider down")

    from app.compare.engine import fan_out_completions

    request = _base_request(["m1", "m2"])
    results = await fan_out_completions(
        request=request,
        key=_key(),
        db=AsyncMock(),
        outer_request_id="req_005",
        comparison_id="cmp_005",
    )

    assert len(results) == 2
    assert all(r.error is not None for r in results)


# ── run_comparison ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_upstream_key", new_callable=AsyncMock)
@patch("app.compare.engine.get_adapter")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_run_comparison_success(
    mock_routing, mock_get_adapter, mock_upstream_key, mock_fire_log
):
    mock_routing.return_value = ("openrouter", "comp-model", None)
    mock_upstream_key.return_value = "sk-test"
    mock_get_adapter.return_value = _mock_adapter("Model A is better.")

    from app.compare.engine import run_comparison
    from app.schemas.compare import ModelCompareResult

    results = [
        ModelCompareResult(
            model="a", content="answer a", latency_ms=100, request_id="r::a"
        ),
        ModelCompareResult(
            model="b", content="answer b", latency_ms=200, request_id="r::b"
        ),
    ]

    with patch("app.compare.engine.settings") as mock_settings:
        mock_settings.compare_fallback_models_list = []
        mock_settings.compare_model_timeout_s = 120.0

        text, usage, model_used, fallback_used = await run_comparison(
            comparison_model="comp-model",
            original_messages=[Message(role="user", content="test")],
            results=results,
            custom_instructions=None,
            key=_key(),
            db=AsyncMock(),
            outer_request_id="req_010",
            comparison_id="cmp_010",
        )

    assert text == "Model A is better."
    assert usage is not None
    assert usage.prompt_tokens == 10
    assert model_used == "comp-model"
    assert fallback_used is False


@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_run_comparison_failure_returns_none(mock_routing, mock_fire_log):
    mock_routing.side_effect = Exception("comparison LLM down")

    with patch("app.compare.engine.settings") as mock_settings:
        mock_settings.compare_fallback_models_list = []
        mock_settings.compare_model_timeout_s = 120.0

        from app.compare.engine import run_comparison

        text, usage, model_used, fallback_used = await run_comparison(
            comparison_model="comp-model",
            original_messages=[Message(role="user", content="test")],
            results=[],
            custom_instructions=None,
            key=_key(),
            db=AsyncMock(),
            outer_request_id="req_011",
            comparison_id="cmp_011",
        )

    assert text is None
    assert usage is None
    assert model_used is None
    assert fallback_used is False


@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_upstream_key", new_callable=AsyncMock)
@patch("app.compare.engine.get_adapter")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_run_comparison_uses_fallback_when_primary_fails(
    mock_routing, mock_get_adapter, mock_upstream_key, mock_fire_log
):
    call_count = {"n": 0}

    def routing_side_effect(model, db):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("primary down")
        return ("openrouter", model, None)

    mock_routing.side_effect = routing_side_effect
    mock_upstream_key.return_value = "sk-test"
    mock_get_adapter.return_value = _mock_adapter("fallback comparison text")

    from app.compare.engine import run_comparison
    from app.schemas.compare import ModelCompareResult

    results = [
        ModelCompareResult(model="a", content="answer a", latency_ms=100, request_id="r::a"),
        ModelCompareResult(model="b", content="answer b", latency_ms=100, request_id="r::b"),
    ]

    with patch("app.compare.engine.settings") as mock_settings:
        mock_settings.compare_fallback_models_list = ["anthropic/claude-3-5-haiku"]
        mock_settings.compare_model_timeout_s = 120.0

        text, usage, model_used, fallback_used = await run_comparison(
            comparison_model="openai/gpt-4o-mini",
            original_messages=[Message(role="user", content="test")],
            results=results,
            custom_instructions=None,
            key=_key(),
            db=AsyncMock(),
            outer_request_id="req_012",
            comparison_id="cmp_012",
        )

    assert text == "fallback comparison text"
    assert model_used == "anthropic/claude-3-5-haiku"
    assert fallback_used is True


@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_run_comparison_all_fallbacks_fail_returns_none(mock_routing, mock_fire_log):
    mock_routing.side_effect = Exception("everything down")

    from app.compare.engine import run_comparison

    with patch("app.compare.engine.settings") as mock_settings:
        mock_settings.compare_fallback_models_list = ["fallback-a", "fallback-b"]
        mock_settings.compare_model_timeout_s = 120.0

        text, usage, model_used, fallback_used = await run_comparison(
            comparison_model="primary",
            original_messages=[Message(role="user", content="test")],
            results=[],
            custom_instructions=None,
            key=_key(),
            db=AsyncMock(),
            outer_request_id="req_013",
            comparison_id="cmp_013",
        )

    assert text is None
    assert model_used is None
    assert fallback_used is False


# ── result ordering ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_upstream_key", new_callable=AsyncMock)
@patch("app.compare.engine.get_adapter")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_fan_out_results_in_input_order(
    mock_routing, mock_get_adapter, mock_upstream_key, mock_fire_log
):
    """asyncio.gather preserves input order."""
    adapters = {
        "slow": _mock_adapter("slow response"),
        "fast": _mock_adapter("fast response"),
    }

    async def slow_completion(req, **kwargs):
        await asyncio.sleep(0.05)
        return {"choices": [{"message": {"content": "slow response"}}], "usage": {}}

    adapters["slow"].chat_completion = slow_completion

    def get_adapter_side_effect(provider):
        # Return same adapter but differentiated by which was called
        return _mock_adapter("default")

    mock_routing.return_value = ("openrouter", "m", None)
    mock_upstream_key.return_value = "sk"
    mock_get_adapter.return_value = _mock_adapter()

    from app.compare.engine import fan_out_completions

    request = _base_request(["model-x", "model-y", "model-z"])
    results = await fan_out_completions(
        request=request,
        key=_key(),
        db=AsyncMock(),
        outer_request_id="req_020",
        comparison_id="cmp_020",
    )

    assert [r.model for r in results] == ["model-x", "model-y", "model-z"]


# ── _stream_single_model_into_queue ──────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_upstream_key", new_callable=AsyncMock)
@patch("app.compare.engine.get_adapter")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_stream_single_model_puts_chunks_then_sentinel(
    mock_routing, mock_get_adapter, mock_upstream_key, mock_fire_log
):
    mock_routing.return_value = ("openrouter", "model-a", None)
    mock_upstream_key.return_value = "sk-test"

    chunk1 = b'data: {"choices":[{"delta":{"content":"hello"},"finish_reason":null}]}\n\n'
    chunk2 = b'data: {"choices":[{"delta":{"content":" world"},"finish_reason":"stop"}]}\n\n'

    async def fake_stream(*args, **kwargs):
        yield chunk1
        yield chunk2

    adapter = MagicMock()
    adapter.stream_chat_completion = MagicMock(return_value=fake_stream())
    mock_get_adapter.return_value = adapter

    from app.compare.engine import _stream_single_model_into_queue

    queue: asyncio.Queue = asyncio.Queue()
    request = _base_request(["model-a"])
    await _stream_single_model_into_queue(
        model="model-a",
        messages=request.messages,
        base_request=request,
        override=None,
        key=_key(),
        db=AsyncMock(),
        outer_request_id="req_030",
        comparison_id="cmp_030",
        queue=queue,
    )

    items = []
    while not queue.empty():
        items.append(queue.get_nowait())

    chunks = [(m, c) for m, c, e in items if c is not None]
    sentinels = [(m, e) for m, c, e in items if c is None]

    assert len(chunks) == 2
    assert chunks[0][1]["delta"] == "hello"
    assert chunks[0][1]["finish_reason"] is None
    assert chunks[1][1]["delta"] == " world"
    assert chunks[1][1]["finish_reason"] == "stop"
    assert len(sentinels) == 1
    assert sentinels[0][1] is None  # clean end, no error


@pytest.mark.asyncio
@patch("app.compare.engine.fire_usage_log")
@patch("app.compare.engine.resolve_routing", new_callable=AsyncMock)
async def test_stream_single_model_puts_error_sentinel_on_failure(mock_routing, mock_fire_log):
    mock_routing.side_effect = Exception("provider down")

    from app.compare.engine import _stream_single_model_into_queue

    queue: asyncio.Queue = asyncio.Queue()
    request = _base_request(["bad-model"])
    await _stream_single_model_into_queue(
        model="bad-model",
        messages=request.messages,
        base_request=request,
        override=None,
        key=_key(),
        db=AsyncMock(),
        outer_request_id="req_031",
        comparison_id="cmp_031",
        queue=queue,
    )

    items = []
    while not queue.empty():
        items.append(queue.get_nowait())

    assert len(items) == 1
    model, chunk, error = items[0]
    assert chunk is None
    assert error is not None
    assert "provider down" in error
