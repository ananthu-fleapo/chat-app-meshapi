"""
Unit tests for per-1M token pricing support.

Covers:
  _per_1m()           — conversion helper in models.py and admin.py
  _resolve_per_1k()   — unit-agnostic input resolver in admin.py
  ModelPriceIn        — resolver methods, dual-unit rejection, required-field guard
  ModelPriceUpdateIn  — optional resolver methods, dual-unit rejection
  ModelPriceOut       — per-1M output fields present and correct
  _to_price_out()     — serialises per-1M alongside per-1K
  ModelPricing        — public schema carries per-1M fields
  _row_to_model_out() — populates per-1M from ORM row
  _apply_discounts()  — discounted per-1M derived correctly
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

# ── helpers imported directly so tests are pure-unit (no app startup needed) ──
from app.routers.models import ModelPricing, ModelOut, _per_1m as models_per_1m, _row_to_model_out
from app.routers.admin import (
    ModelPriceIn,
    ModelPriceOut,
    ModelPriceUpdateIn,
    _per_1m as admin_per_1m,
    _resolve_per_1k,
    _to_price_out,
)


# ─────────────────────────────────────────────────────────────────────────────
# _per_1m — shared conversion helper (tested via both import sites)
# ─────────────────────────────────────────────────────────────────────────────

class TestPerOneMHelper:

    @pytest.mark.parametrize("helper", [models_per_1m, admin_per_1m])
    def test_none_returns_none(self, helper):
        assert helper(None) is None

    @pytest.mark.parametrize("helper", [models_per_1m, admin_per_1m])
    def test_zero_returns_zero_decimal(self, helper):
        # Decimal.quantize(0) → "0E-8" in Python's repr, but its value is zero.
        # We assert decimal equality rather than string equality for the zero case.
        result = helper(Decimal("0"))
        assert result is not None
        assert Decimal(result) == Decimal("0")

    @pytest.mark.parametrize("helper", [models_per_1m, admin_per_1m])
    def test_basic_conversion(self, helper):
        """$0.0025 / 1K → $2.50 / 1M"""
        assert helper(Decimal("0.00250000")) == "2.50000000"

    @pytest.mark.parametrize("helper", [models_per_1m, admin_per_1m])
    def test_claude_opus_rate(self, helper):
        """$0.015 / 1K → $15 / 1M"""
        assert helper(Decimal("0.01500000")) == "15.00000000"

    @pytest.mark.parametrize("helper", [models_per_1m, admin_per_1m])
    def test_tiny_value_no_precision_loss(self, helper):
        """Smallest storable value: $0.00000001 / 1K → $0.00001 / 1M"""
        assert helper(Decimal("0.00000001")) == "0.00001000"

    @pytest.mark.parametrize("helper", [models_per_1m, admin_per_1m])
    def test_returns_string(self, helper):
        result = helper(Decimal("0.00500000"))
        assert isinstance(result, str)

    @pytest.mark.parametrize("helper", [models_per_1m, admin_per_1m])
    def test_quantized_to_8_decimal_places(self, helper):
        result = helper(Decimal("0.00250000"))
        assert result is not None
        _, _, exp = Decimal(result).as_tuple()
        assert exp == -8

    @pytest.mark.parametrize("helper", [models_per_1m, admin_per_1m])
    def test_upstream_style_tiny_rate(self, helper):
        """$0.00015 / 1K (GPT-4o-mini input) → $0.15 / 1M"""
        assert helper(Decimal("0.00015000")) == "0.15000000"


# ─────────────────────────────────────────────────────────────────────────────
# _resolve_per_1k — unit-agnostic input converter
# ─────────────────────────────────────────────────────────────────────────────

class TestResolvePerOneK:

    def test_per_1k_input_returned_as_decimal(self):
        result = _resolve_per_1k(0.0025, None, "prompt")
        assert result == Decimal("0.00250000")

    def test_per_1m_input_converted_to_per_1k(self):
        result = _resolve_per_1k(None, 2.5, "prompt")
        assert result == Decimal("0.00250000")

    def test_both_none_returns_none(self):
        assert _resolve_per_1k(None, None, "prompt") is None

    def test_dual_unit_raises_value_error(self):
        with pytest.raises(ValueError, match="not both"):
            _resolve_per_1k(0.0025, 2.5, "prompt")

    def test_per_1m_uses_decimal_str_conversion(self):
        """Float 10.0 / 1000 must produce exact Decimal, not 0.009999..."""
        result = _resolve_per_1k(None, 10.0, "completion")
        assert result == Decimal("0.01000000")

    def test_per_1k_zero(self):
        result = _resolve_per_1k(0.0, None, "prompt")
        assert result == Decimal("0.00000000")

    def test_per_1m_zero(self):
        result = _resolve_per_1k(None, 0.0, "prompt")
        assert result == Decimal("0.00000000")

    def test_high_value_per_1m(self):
        """$30 / 1M (Claude Opus) → $0.03 / 1K"""
        result = _resolve_per_1k(None, 30.0, "prompt")
        assert result == Decimal("0.03000000")

    def test_field_name_appears_in_error(self):
        with pytest.raises(ValueError, match="upstream_prompt"):
            _resolve_per_1k(0.001, 1.0, "upstream_prompt")

    def test_result_quantized_to_8_places(self):
        result = _resolve_per_1k(None, 2.5, "prompt")
        _, _, exp = result.as_tuple()
        assert exp == -8


# ─────────────────────────────────────────────────────────────────────────────
# ModelPriceIn — resolver methods and validation
# ─────────────────────────────────────────────────────────────────────────────

class TestModelPriceIn:

    def _make(self, **kwargs):
        defaults = dict(model_id="test/model", provider="openrouter", is_default=False)
        defaults.update(kwargs)
        return ModelPriceIn(**defaults)

    # ── resolved_prompt ───────────────────────────────────────────────────────

    def test_resolved_prompt_from_per_1k(self):
        m = self._make(prompt_usd_per_1k=0.0025, completion_usd_per_1k=0.01)
        assert m.resolved_prompt() == Decimal("0.00250000")

    def test_resolved_prompt_from_per_1m(self):
        m = self._make(prompt_usd_per_1m=2.5, completion_usd_per_1m=10.0)
        assert m.resolved_prompt() == Decimal("0.00250000")

    def test_resolved_completion_from_per_1k(self):
        m = self._make(prompt_usd_per_1k=0.0025, completion_usd_per_1k=0.01)
        assert m.resolved_completion() == Decimal("0.01000000")

    def test_resolved_completion_from_per_1m(self):
        m = self._make(prompt_usd_per_1m=2.5, completion_usd_per_1m=10.0)
        assert m.resolved_completion() == Decimal("0.01000000")

    # ── dual-unit rejection ───────────────────────────────────────────────────

    def test_dual_prompt_raises(self):
        # Dual-unit conflict is now caught at model construction (Pydantic → 422).
        with pytest.raises(ValidationError, match="not both"):
            self._make(
                prompt_usd_per_1k=0.0025, prompt_usd_per_1m=2.5,
                completion_usd_per_1k=0.01,
            )

    def test_dual_completion_raises(self):
        with pytest.raises(ValidationError, match="not both"):
            self._make(
                prompt_usd_per_1k=0.0025,
                completion_usd_per_1k=0.01, completion_usd_per_1m=10.0,
            )

    # ── required-field guard ──────────────────────────────────────────────────

    def test_missing_prompt_raises(self):
        m = self._make(completion_usd_per_1k=0.01)
        with pytest.raises(ValueError, match="required"):
            m.resolved_prompt()

    def test_missing_completion_raises(self):
        m = self._make(prompt_usd_per_1k=0.0025)
        with pytest.raises(ValueError, match="required"):
            m.resolved_completion()

    # ── upstream resolvers ────────────────────────────────────────────────────

    def test_upstream_prompt_from_per_1k(self):
        m = self._make(
            prompt_usd_per_1k=0.0, completion_usd_per_1k=0.0,
            upstream_prompt_usd_per_1k=0.0015,
        )
        assert m.resolved_upstream_prompt() == Decimal("0.00150000")

    def test_upstream_prompt_from_per_1m(self):
        m = self._make(
            prompt_usd_per_1k=0.0, completion_usd_per_1k=0.0,
            upstream_prompt_usd_per_1m=1.5,
        )
        assert m.resolved_upstream_prompt() == Decimal("0.00150000")

    def test_upstream_none_when_not_supplied(self):
        m = self._make(prompt_usd_per_1k=0.0, completion_usd_per_1k=0.0)
        assert m.resolved_upstream_prompt() is None
        assert m.resolved_upstream_completion() is None

    def test_upstream_dual_raises(self):
        # Upstream dual-unit conflict also caught at construction now.
        with pytest.raises(ValidationError, match="not both"):
            self._make(
                prompt_usd_per_1k=0.0, completion_usd_per_1k=0.0,
                upstream_completion_usd_per_1k=0.01, upstream_completion_usd_per_1m=10.0,
            )

    # ── free model zero pricing ───────────────────────────────────────────────

    def test_free_model_zero_per_1k(self):
        m = self._make(prompt_usd_per_1k=0.0, completion_usd_per_1k=0.0, is_free=True)
        assert m.resolved_prompt() == Decimal("0")
        assert m.resolved_completion() == Decimal("0")

    def test_free_model_zero_per_1m(self):
        m = self._make(prompt_usd_per_1m=0.0, completion_usd_per_1m=0.0, is_free=True)
        assert m.resolved_prompt() == Decimal("0")
        assert m.resolved_completion() == Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# ModelPriceUpdateIn — optional resolvers
# ─────────────────────────────────────────────────────────────────────────────

class TestModelPriceUpdateIn:

    def test_all_none_resolves_none(self):
        m = ModelPriceUpdateIn()
        assert m.resolved_prompt() is None
        assert m.resolved_completion() is None
        assert m.resolved_upstream_prompt() is None
        assert m.resolved_upstream_completion() is None

    def test_prompt_from_per_1k(self):
        m = ModelPriceUpdateIn(prompt_usd_per_1k=0.005)
        assert m.resolved_prompt() == Decimal("0.00500000")

    def test_prompt_from_per_1m(self):
        m = ModelPriceUpdateIn(prompt_usd_per_1m=5.0)
        assert m.resolved_prompt() == Decimal("0.00500000")

    def test_dual_prompt_raises(self):
        # Dual-unit conflict caught at model construction (Pydantic → 422).
        with pytest.raises(ValidationError, match="not both"):
            ModelPriceUpdateIn(prompt_usd_per_1k=0.005, prompt_usd_per_1m=5.0)

    def test_completion_from_per_1m(self):
        m = ModelPriceUpdateIn(completion_usd_per_1m=15.0)
        assert m.resolved_completion() == Decimal("0.01500000")

    def test_upstream_from_per_1m(self):
        m = ModelPriceUpdateIn(upstream_prompt_usd_per_1m=3.0)
        assert m.resolved_upstream_prompt() == Decimal("0.00300000")


# ─────────────────────────────────────────────────────────────────────────────
# _to_price_out — ORM → ModelPriceOut serialisation
# ─────────────────────────────────────────────────────────────────────────────

def _make_orm_price(
    model_id="openai/gpt-4o",
    provider="openrouter",
    is_default=True,
    prompt=Decimal("0.00250000"),
    completion=Decimal("0.01000000"),
    is_free=False,
    up_prompt=None,
    up_completion=None,
):
    row = MagicMock()
    row.model_id = model_id
    row.provider = provider
    row.is_default = is_default
    row.prompt_usd_per_1k = prompt
    row.completion_usd_per_1k = completion
    row.is_free = is_free
    row.upstream_prompt_usd_per_1k = up_prompt
    row.upstream_completion_usd_per_1k = up_completion
    from datetime import datetime, timezone
    row.updated_at = datetime(2026, 4, 8, tzinfo=timezone.utc)
    return row


class TestToPriceOut:

    def test_per_1k_fields_present(self):
        out = _to_price_out(_make_orm_price())
        assert out.prompt_usd_per_1k == "0.00250000"
        assert out.completion_usd_per_1k == "0.01000000"

    def test_per_1m_fields_present(self):
        out = _to_price_out(_make_orm_price())
        assert out.prompt_usd_per_1m == "2.50000000"
        assert out.completion_usd_per_1m == "10.00000000"

    def test_upstream_per_1k_present_when_set(self):
        out = _to_price_out(_make_orm_price(
            up_prompt=Decimal("0.00150000"),
            up_completion=Decimal("0.00750000"),
        ))
        assert out.upstream_prompt_usd_per_1k == "0.00150000"
        assert out.upstream_completion_usd_per_1k == "0.00750000"

    def test_upstream_per_1m_present_when_set(self):
        out = _to_price_out(_make_orm_price(
            up_prompt=Decimal("0.00150000"),
            up_completion=Decimal("0.00750000"),
        ))
        assert out.upstream_prompt_usd_per_1m == "1.50000000"
        assert out.upstream_completion_usd_per_1m == "7.50000000"

    def test_upstream_none_when_not_set(self):
        out = _to_price_out(_make_orm_price())
        assert out.upstream_prompt_usd_per_1k is None
        assert out.upstream_completion_usd_per_1k is None
        assert out.upstream_prompt_usd_per_1m is None
        assert out.upstream_completion_usd_per_1m is None

    def test_is_free_propagated(self):
        out = _to_price_out(_make_orm_price(is_free=True))
        assert out.is_free is True

    def test_returns_model_price_out_type(self):
        out = _to_price_out(_make_orm_price())
        assert isinstance(out, ModelPriceOut)


# ─────────────────────────────────────────────────────────────────────────────
# ModelPricing (public schema) and _row_to_model_out
# ─────────────────────────────────────────────────────────────────────────────

def _make_model_orm(model_id="openai/gpt-4o", name="GPT-4o", context_length=128_000):
    m = MagicMock()
    m.model_id = model_id
    m.name = name
    m.context_length = context_length
    m.description = None
    m.model_type = "text"
    m.input_modalities = ["text"]
    m.output_modalities = ["text"]
    return m


def _make_model_price_orm(
    prompt=Decimal("0.00250000"),
    completion=Decimal("0.01000000"),
    is_free=False,
):
    mp = MagicMock()
    mp.prompt_usd_per_1k = prompt
    mp.completion_usd_per_1k = completion
    mp.is_free = is_free
    mp.supports_thinking = False
    mp.supports_completions_api = True
    mp.supports_responses_api = True
    return mp


class TestRowToModelOut:

    def test_per_1k_fields_populated(self):
        out = _row_to_model_out(_make_model_orm(), _make_model_price_orm())
        assert out.pricing.prompt_usd_per_1k == "0.00250000"
        assert out.pricing.completion_usd_per_1k == "0.01000000"

    def test_per_1m_fields_populated(self):
        out = _row_to_model_out(_make_model_orm(), _make_model_price_orm())
        assert out.pricing.prompt_usd_per_1m == "2.50000000"
        assert out.pricing.completion_usd_per_1m == "10.00000000"

    def test_free_model_per_1k_zero(self):
        out = _row_to_model_out(_make_model_orm(), _make_model_price_orm(is_free=True))
        assert out.pricing.prompt_usd_per_1k == "0"
        assert out.pricing.completion_usd_per_1k == "0"

    def test_free_model_per_1m_zero(self):
        out = _row_to_model_out(_make_model_orm(), _make_model_price_orm(is_free=True))
        assert out.pricing.prompt_usd_per_1m == "0"
        assert out.pricing.completion_usd_per_1m == "0"

    def test_discounted_fields_none_before_discount_applied(self):
        out = _row_to_model_out(_make_model_orm(), _make_model_price_orm())
        assert out.pricing.prompt_usd_per_1k_discounted is None
        assert out.pricing.prompt_usd_per_1m_discounted is None
        assert out.pricing.completion_usd_per_1m_discounted is None

    def test_returns_model_out_type(self):
        out = _row_to_model_out(_make_model_orm(), _make_model_price_orm())
        assert isinstance(out, ModelOut)


# ─────────────────────────────────────────────────────────────────────────────
# _apply_discounts — discounted per-1M derived correctly
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyDiscountsPer1M:
    """
    Test that _apply_discounts() correctly populates per-1M discounted fields.
    We test the _discounted() inner function indirectly via ModelPricing mutation.
    """

    def _make_model_out(self, prompt_1k="0.00250000", completion_1k="0.01000000"):
        pricing = ModelPricing(
            prompt_usd_per_1k=prompt_1k,
            completion_usd_per_1k=completion_1k,
            prompt_usd_per_1m=str((Decimal(prompt_1k) * 1000).quantize(Decimal("0.00000001"))),
            completion_usd_per_1m=str((Decimal(completion_1k) * 1000).quantize(Decimal("0.00000001"))),
        )
        m = MagicMock(spec=ModelOut)
        m.is_free = False
        m.id = "openai/gpt-4o"
        m.pricing = pricing
        return m

    @pytest.mark.asyncio
    async def test_discounted_per_1m_prompt(self):
        """20% discount on $2.50/1M → $2.00/1M"""
        from datetime import UTC, datetime
        from unittest.mock import AsyncMock, patch

        from app.routers.models import _apply_discounts

        model = self._make_model_out()
        mock_result = MagicMock()
        mock_result.all.return_value = [(None, Decimal("20"))]  # account-level 20% discount

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.routers.models.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 8, tzinfo=UTC)
            result = await _apply_discounts([model], "user_1", mock_db)

        m = result[0]
        assert m.pricing.prompt_usd_per_1m_discounted == "2.00000000"
        assert m.pricing.completion_usd_per_1m_discounted == "8.00000000"

    @pytest.mark.asyncio
    async def test_discounted_per_1k_still_present(self):
        """per-1K discounted field must coexist with per-1M discounted."""
        from datetime import UTC, datetime
        from unittest.mock import AsyncMock, patch

        from app.routers.models import _apply_discounts

        model = self._make_model_out()
        mock_result = MagicMock()
        mock_result.all.return_value = [(None, Decimal("10"))]  # 10% discount

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.routers.models.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 8, tzinfo=UTC)
            result = await _apply_discounts([model], "user_1", mock_db)

        m = result[0]
        assert m.pricing.prompt_usd_per_1k_discounted == "0.00225000"
        assert m.pricing.prompt_usd_per_1m_discounted == "2.25000000"

    @pytest.mark.asyncio
    async def test_free_model_skipped(self):
        """Free models pass through without discount fields being set."""
        from datetime import UTC, datetime
        from unittest.mock import AsyncMock, patch

        from app.routers.models import _apply_discounts

        model = self._make_model_out()
        model.is_free = True
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        with patch("app.routers.models.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 8, tzinfo=UTC)
            result = await _apply_discounts([model], "user_1", mock_db)

        m = result[0]
        assert m.pricing.prompt_usd_per_1m_discounted is None

    @pytest.mark.asyncio
    async def test_no_discount_leaves_fields_none(self):
        """No active discount → discounted fields stay None."""
        from datetime import UTC, datetime
        from unittest.mock import AsyncMock, patch

        from app.routers.models import _apply_discounts

        model = self._make_model_out()
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        with patch("app.routers.models.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 8, tzinfo=UTC)
            result = await _apply_discounts([model], "user_1", mock_db)

        m = result[0]
        assert m.pricing.prompt_usd_per_1m_discounted is None
        assert m.pricing.completion_usd_per_1m_discounted is None


# ─────────────────────────────────────────────────────────────────────────────
# Edge cases and precision cross-checks
# ─────────────────────────────────────────────────────────────────────────────

class TestPrecisionEdgeCases:

    def test_per_1m_to_per_1k_roundtrip(self):
        """per-1M → stored per-1K → back to per-1M produces the same value."""
        original_per_1m = 2.5
        stored_per_1k = _resolve_per_1k(None, original_per_1m, "prompt")
        assert stored_per_1k is not None
        back_to_per_1m = admin_per_1m(stored_per_1k)
        assert back_to_per_1m == "2.50000000"

    def test_high_precision_rate(self):
        """$3.75 / 1M → $0.00375 / 1K (three decimal places)"""
        stored = _resolve_per_1k(None, 3.75, "prompt")
        assert stored is not None
        assert admin_per_1m(stored) == "3.75000000"

    def test_sub_cent_rate(self):
        """$0.10 / 1M → $0.0001 / 1K"""
        stored = _resolve_per_1k(None, 0.10, "prompt")
        assert stored is not None
        assert stored == Decimal("0.00010000")

    @pytest.mark.parametrize("per_1m,expected_per_1k", [
        (2.50,   "0.00250000"),   # GPT-4o input
        (10.0,   "0.01000000"),   # GPT-4o output
        (15.0,   "0.01500000"),   # Claude Sonnet output
        (75.0,   "0.07500000"),   # Claude Opus output
        (0.075,  "0.00007500"),   # Very cheap model
        (0.0,    "0.00000000"),   # Free (compared as Decimal, not string)
    ])
    def test_per_1m_input_parametrized(self, per_1m, expected_per_1k):
        result = _resolve_per_1k(None, per_1m, "test")
        assert result is not None
        assert Decimal(str(result)) == Decimal(expected_per_1k)

    @pytest.mark.parametrize("per_1k,expected_per_1m", [
        (Decimal("0.00250000"), "2.50000000"),
        (Decimal("0.01000000"), "10.00000000"),
        (Decimal("0.01500000"), "15.00000000"),
        (Decimal("0.07500000"), "75.00000000"),
        (Decimal("0.00007500"), "0.07500000"),
        (Decimal("0.00000000"), "0.00000000"),
    ])
    def test_per_1k_to_per_1m_parametrized(self, per_1k, expected_per_1m):
        result = admin_per_1m(per_1k)
        assert result is not None
        assert Decimal(result) == Decimal(expected_per_1m)
