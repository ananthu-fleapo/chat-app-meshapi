"""
Unit tests for app/usage/logger.py

Covers:
  _our_cost       — model_prices DB hit, DB miss → static fallback,
                    is_free model, DB error → static fallback
  log_usage_event — success+cost>0 deducts balance, error status skips deduct,
                    success+None cost skips deduct, prompt_tokens=None skips cost,
                    DB write failure silently swallowed
  fire_usage_log  — schedules asyncio.create_task
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

KEY_ID = "00000000-0000-0000-0000-000000000001"
REQUEST_ID = "req_test_001"
MODEL = "openai/gpt-4o"
OWNER = "acme"


def _make_session_factory(session):
    """Build a mock get_session_factory that yields the given session."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=cm)
    return MagicMock(return_value=factory)


def _make_write_session():
    """Session mock suitable for the usage event write path."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    # Return a plain MagicMock so that result methods like scalar_one_or_none()
    # don't produce unawaited coroutines (Python 3.13 warns on this).
    session.execute = AsyncMock(return_value=MagicMock())
    return session


# ── _our_cost ─────────────────────────────────────────────────────────────────

def _make_model_price_row(
    is_free: bool = False,
    prompt: float = 0.002500,
    completion: float = 0.010000,
    upstream_prompt: float | None = None,
    upstream_completion: float | None = None,
) -> MagicMock:
    """Build a ModelPrice-like mock for _lookup_model_price return value."""
    mp = MagicMock()
    mp.is_free = is_free
    mp.prompt_usd_per_1k = prompt
    mp.completion_usd_per_1k = completion
    mp.upstream_prompt_usd_per_1k = upstream_prompt
    mp.upstream_completion_usd_per_1k = upstream_completion
    return mp


# ── _calc_upstream_cost ───────────────────────────────────────────────────────

class TestCalcUpstreamCost:

    async def test_returns_calculated_cost_when_upstream_rates_configured(self):
        """upstream_*_usd_per_1k set → cost = tokens × rates."""
        from app.usage.logger import _calc_upstream_cost

        row = _make_model_price_row(upstream_prompt=0.003, upstream_completion=0.015)
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=row)))
        sf = _make_session_factory(session)

        with patch("app.usage.logger.get_session_factory", sf):
            cost = await _calc_upstream_cost("anthropic/claude-3-5-sonnet", "bedrock", 1000, 500)

        # (0.003 * 1000/1000) + (0.015 * 500/1000) = 0.003 + 0.0075 = 0.0105
        assert cost == Decimal("0.01050000")

    async def test_returns_none_when_no_row_found(self):
        """Model not in model_prices → None."""
        from app.usage.logger import _calc_upstream_cost

        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        sf = _make_session_factory(session)

        with patch("app.usage.logger.get_session_factory", sf):
            cost = await _calc_upstream_cost("unknown/model", "vertex", 1000, 500)

        assert cost is None

    async def test_returns_none_when_upstream_rates_not_set(self):
        """Row exists but upstream_prompt_usd_per_1k is None → None."""
        from app.usage.logger import _calc_upstream_cost

        row = _make_model_price_row(upstream_prompt=None, upstream_completion=None)
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=row)))
        sf = _make_session_factory(session)

        with patch("app.usage.logger.get_session_factory", sf):
            cost = await _calc_upstream_cost("openai/gpt-4o", "openai", 1000, 500)

        assert cost is None

    async def test_db_error_returns_none_silently(self):
        """DB failure returns None without raising."""
        from app.usage.logger import _calc_upstream_cost

        sf = MagicMock(side_effect=RuntimeError("db down"))

        with patch("app.usage.logger.get_session_factory", sf):
            cost = await _calc_upstream_cost("some/model", "bedrock", 100, 50)

        assert cost is None


class TestOurCost:

    async def test_model_prices_hit_returns_computed_cost(self):
        """Row found in model_prices → compute and return our cost."""
        from app.usage.logger import _our_cost

        row = _make_model_price_row(is_free=False, prompt=0.002500, completion=0.010000)
        sf = _make_session_factory(AsyncMock())
        with patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.balance._lookup_model_price", AsyncMock(return_value=row)):
            cost = await _our_cost(MODEL, 1000, 1000)

        # 0.0025 + 0.01 = 0.0125
        assert cost == Decimal("0.01250000")

    async def test_model_prices_miss_falls_back_to_static_table(self):
        """No row in model_prices → falls back to calculate_cost()."""
        from app.usage.logger import _our_cost

        sf = _make_session_factory(AsyncMock())
        with patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.balance._lookup_model_price", AsyncMock(return_value=None)):
            cost = await _our_cost(MODEL, 1000, 1000)

        # Falls back to static pricing for gpt-4o: 0.0025 + 0.01 = 0.0125
        assert cost == Decimal("0.01250000")

    async def test_is_free_model_returns_zero(self):
        """Model marked is_free=True in model_prices → cost = Decimal('0')."""
        from app.usage.logger import _our_cost

        row = _make_model_price_row(is_free=True)
        sf = _make_session_factory(AsyncMock())
        with patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.balance._lookup_model_price", AsyncMock(return_value=row)):
            cost = await _our_cost(MODEL, 1000, 1000)

        assert cost == Decimal("0")

    async def test_db_error_falls_back_to_static_table(self):
        """model_prices query fails → silently falls back to static pricing."""
        from app.usage.logger import _our_cost

        sf = MagicMock(side_effect=Exception("DB unavailable"))
        with patch("app.usage.logger.get_session_factory", sf):
            cost = await _our_cost(MODEL, 1000, 1000)

        # Static table fallback for gpt-4o
        assert cost == Decimal("0.01250000")

    async def test_unknown_model_returns_none(self):
        """Unknown model in both DB and static table → None."""
        from app.usage.logger import _our_cost

        sf = _make_session_factory(AsyncMock())
        with patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.balance._lookup_model_price", AsyncMock(return_value=None)):
            cost = await _our_cost("unknown/model-xyz", 100, 100)

        assert cost is None


# ── log_usage_event ───────────────────────────────────────────────────────────

class TestLogUsageEvent:

    def _log_kwargs(self, **overrides):
        base = dict(
            key_id=KEY_ID,
            owner=OWNER,
            request_id=REQUEST_ID,
            model=MODEL,
            template_id=None,
            stream=False,
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=200,
            status="success",
        )
        base.update(overrides)
        return base

    async def test_success_with_cost_deducts_balance(self):
        """status=success + cost>0 → deduct_balance is called."""
        from app.usage.logger import log_usage_event

        write_session = _make_write_session()
        sf = _make_session_factory(write_session)

        with patch("app.usage.logger._our_cost", AsyncMock(return_value=Decimal("0.01"))), \
             patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.balance.deduct_balance", AsyncMock()) as mock_deduct, \
             patch("app.metrics.record_inference", MagicMock()):
            await log_usage_event(**self._log_kwargs(status="success"))

        mock_deduct.assert_called_once_with(OWNER, Decimal("0.01"))

    async def test_error_status_does_not_deduct_balance(self):
        """status=error → deduct_balance is NOT called."""
        from app.usage.logger import log_usage_event

        write_session = _make_write_session()
        sf = _make_session_factory(write_session)

        with patch("app.usage.logger._our_cost", AsyncMock(return_value=Decimal("0.01"))), \
             patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.balance.deduct_balance", AsyncMock()) as mock_deduct, \
             patch("app.metrics.record_inference", MagicMock()):
            await log_usage_event(**self._log_kwargs(status="error"))

        mock_deduct.assert_not_called()

    async def test_success_with_none_cost_does_not_deduct_balance(self):
        """status=success but cost=None → deduct_balance is NOT called."""
        from app.usage.logger import log_usage_event

        write_session = _make_write_session()
        sf = _make_session_factory(write_session)

        with patch("app.usage.logger._our_cost", AsyncMock(return_value=None)), \
             patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.balance.deduct_balance", AsyncMock()) as mock_deduct, \
             patch("app.metrics.record_inference", MagicMock()):
            await log_usage_event(**self._log_kwargs(status="success"))

        mock_deduct.assert_not_called()

    async def test_none_prompt_tokens_skips_cost_computation(self):
        """prompt_tokens=None → _our_cost is never called, cost remains None."""
        from app.usage.logger import log_usage_event

        write_session = _make_write_session()
        sf = _make_session_factory(write_session)

        with patch("app.usage.logger._our_cost", AsyncMock()) as mock_our_cost, \
             patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.balance.deduct_balance", AsyncMock()), \
             patch("app.metrics.record_inference", MagicMock()):
            await log_usage_event(**self._log_kwargs(prompt_tokens=None, completion_tokens=None))

        mock_our_cost.assert_not_called()

    async def test_db_write_failure_silently_swallowed(self):
        """DB error during event write → no exception propagates."""
        from app.usage.logger import log_usage_event

        # Make the session factory raise on commit
        write_session = _make_write_session()
        write_session.commit = AsyncMock(side_effect=Exception("DB write failed"))
        sf = _make_session_factory(write_session)

        with patch("app.usage.logger._our_cost", AsyncMock(return_value=Decimal("0.01"))), \
             patch("app.usage.logger.get_session_factory", sf):
            # Must not raise
            await log_usage_event(**self._log_kwargs(status="success"))


    async def test_upstream_cost_calculated_from_rates_when_not_provided(self):
        """
        When upstream_cost is None (non-OpenRouter) but tokens are known,
        upstream_cost_usd in the written event should come from _calc_upstream_cost.
        """
        from app.usage.logger import log_usage_event

        write_session = _make_write_session()
        sf = _make_session_factory(write_session)
        calc_result = Decimal("0.00750000")

        with patch("app.usage.logger._our_cost", AsyncMock(return_value=Decimal("0.01"))), \
             patch("app.usage.logger._calc_upstream_cost", AsyncMock(return_value=calc_result)) as mock_calc, \
             patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.balance.deduct_balance", AsyncMock()), \
             patch("app.metrics.record_inference", MagicMock()):
            await log_usage_event(**self._log_kwargs(
                status="success",
                provider="bedrock",
                upstream_cost=None,       # provider didn't report cost
                prompt_tokens=500,
                completion_tokens=250,
            ))

        mock_calc.assert_called_once_with(MODEL, "bedrock", 500, 250)
        # Verify the UsageEvent was created with the calculated upstream cost
        added_event = write_session.add.call_args[0][0]
        assert added_event.upstream_cost_usd == calc_result

    async def test_upstream_cost_from_provider_takes_priority_over_calculated(self):
        """When upstream_cost is provided (OpenRouter), _calc_upstream_cost is not called."""
        from app.usage.logger import log_usage_event

        write_session = _make_write_session()
        sf = _make_session_factory(write_session)

        with patch("app.usage.logger._our_cost", AsyncMock(return_value=Decimal("0.01"))), \
             patch("app.usage.logger._calc_upstream_cost", AsyncMock()) as mock_calc, \
             patch("app.usage.logger.get_session_factory", sf), \
             patch("app.usage.balance.deduct_balance", AsyncMock()), \
             patch("app.metrics.record_inference", MagicMock()):
            await log_usage_event(**self._log_kwargs(
                status="success",
                upstream_cost=0.0085,     # OpenRouter reported it directly
            ))

        mock_calc.assert_not_called()


# ── fire_usage_log ────────────────────────────────────────────────────────────

class TestFireUsageLog:

    async def test_schedules_create_task(self):
        """fire_usage_log wraps log_usage_event in asyncio.create_task."""
        from app.usage.logger import fire_usage_log

        with patch.object(asyncio, "create_task") as mock_ct:
            fire_usage_log(
                owner=OWNER,
                key_id=KEY_ID,
                request_id=REQUEST_ID,
                model=MODEL,
                template_id=None,
                stream=False,
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=200,
                status="success",
            )
        mock_ct.assert_called_once()
        # Close the coroutine to avoid "never awaited" RuntimeWarning
        mock_ct.call_args[0][0].close()
