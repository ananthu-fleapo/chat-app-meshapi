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
    return session


# ── _our_cost ─────────────────────────────────────────────────────────────────

class TestOurCost:

    async def test_model_prices_hit_returns_computed_cost(self):
        """Row found in model_prices → compute and return our cost."""
        from app.usage.logger import _our_cost

        mock_session = AsyncMock()
        result = MagicMock()
        # (prompt_usd_per_1k, completion_usd_per_1k, is_free)
        result.one_or_none.return_value = (0.002500, 0.010000, False)
        mock_session.execute = AsyncMock(return_value=result)

        sf = _make_session_factory(mock_session)
        with patch("app.usage.logger.get_session_factory", sf):
            cost = await _our_cost(MODEL, 1000, 1000)

        # 0.0025 + 0.01 = 0.0125
        assert cost == Decimal("0.01250000")

    async def test_model_prices_miss_falls_back_to_static_table(self):
        """No row in model_prices → falls back to calculate_cost()."""
        from app.usage.logger import _our_cost

        mock_session = AsyncMock()
        result = MagicMock()
        result.one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result)

        sf = _make_session_factory(mock_session)
        with patch("app.usage.logger.get_session_factory", sf):
            cost = await _our_cost(MODEL, 1000, 1000)

        # Falls back to static pricing for gpt-4o: 0.0025 + 0.01 = 0.0125
        assert cost == Decimal("0.01250000")

    async def test_is_free_model_returns_zero(self):
        """Model marked is_free=True in model_prices → cost = Decimal('0')."""
        from app.usage.logger import _our_cost

        mock_session = AsyncMock()
        result = MagicMock()
        result.one_or_none.return_value = (0.0, 0.0, True)
        mock_session.execute = AsyncMock(return_value=result)

        sf = _make_session_factory(mock_session)
        with patch("app.usage.logger.get_session_factory", sf):
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

        mock_session = AsyncMock()
        result = MagicMock()
        result.one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result)

        sf = _make_session_factory(mock_session)
        with patch("app.usage.logger.get_session_factory", sf):
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
