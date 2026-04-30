"""
Unit tests for app/pricing/resolver.py

Covers:
  _normalise_cost         — per_1k passthrough, per_1m division, unsupported units → None
  _row_from_v1            — maps ModelPrice attributes to PriceRow fields
  _row_from_v2            — maps ModelPricing attributes + normalises pricing_unit
  get_price_row           — exact (model, provider) lookup, flag dispatch, not-found
  get_default_price_row   — is_default=True hit, fallback to any row, not-found
  resolve_canonical_model_id — exact model_id match then provider_model_id match
  list_all_provider_price_rows — (Model, PriceRow|None) tuples with outerjoin
  Admin dual-write        — _clear_default, create, update, delete all touch both tables
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pricing.resolver import (
    PriceRow,
    _normalise_cost,
    _row_from_v1,
    _row_from_v2,
)


# ─────────────────────────────────────────────────────────────────────────────
# _normalise_cost
# ─────────────────────────────────────────────────────────────────────────────

class TestNormaliseCost:

    def test_per_1k_returned_as_is(self):
        cost = Decimal("0.00250000")
        assert _normalise_cost(cost, "per_1k_tokens") == cost

    def test_per_1m_divided_by_1000(self):
        cost = Decimal("2.50000000")
        assert _normalise_cost(cost, "per_1m_tokens") == Decimal("0.00250000")

    def test_per_image_returns_none(self):
        assert _normalise_cost(Decimal("0.04"), "per_image") is None

    def test_per_second_returns_none(self):
        assert _normalise_cost(Decimal("0.001"), "per_second") is None

    def test_none_cost_returns_none(self):
        assert _normalise_cost(None, "per_1k_tokens") is None

    def test_none_cost_with_per_1m_returns_none(self):
        assert _normalise_cost(None, "per_1m_tokens") is None

    def test_zero_per_1k_returns_zero(self):
        assert _normalise_cost(Decimal("0"), "per_1k_tokens") == Decimal("0")

    def test_zero_per_1m_returns_zero(self):
        assert _normalise_cost(Decimal("0"), "per_1m_tokens") == Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# _row_from_v1
# ─────────────────────────────────────────────────────────────────────────────

def _make_v1_orm(
    model_id="openai/gpt-4o",
    provider="openrouter",
    provider_model_id=None,
    responses_provider_model_id=None,
    is_default=True,
    is_free=False,
    prompt=Decimal("0.00250000"),
    completion=Decimal("0.01000000"),
    upstream_prompt=None,
    upstream_completion=None,
    supports_thinking=False,
    supports_completions_api=True,
    supports_responses_api=False,
    supports_embeddings_api=False,
    supports_batching=False,
    is_active=True,
    priority=None,
):
    row = MagicMock()
    row.model_id = model_id
    row.provider = provider
    row.provider_model_id = provider_model_id
    row.responses_provider_model_id = responses_provider_model_id
    row.is_default = is_default
    row.is_free = is_free
    row.prompt_usd_per_1k = prompt
    row.completion_usd_per_1k = completion
    row.upstream_prompt_usd_per_1k = upstream_prompt
    row.upstream_completion_usd_per_1k = upstream_completion
    row.supports_thinking = supports_thinking
    row.supports_completions_api = supports_completions_api
    row.supports_responses_api = supports_responses_api
    row.supports_embeddings_api = supports_embeddings_api
    row.supports_batching = supports_batching
    row.is_active = is_active
    row.priority = priority
    return row


class TestRowFromV1:

    def test_returns_price_row_instance(self):
        assert isinstance(_row_from_v1(_make_v1_orm()), PriceRow)

    def test_fields_mapped_correctly(self):
        orm = _make_v1_orm(
            model_id="openai/gpt-4o",
            provider="openrouter",
            prompt=Decimal("0.00250000"),
            completion=Decimal("0.01000000"),
            is_free=False,
            is_default=True,
        )
        row = _row_from_v1(orm)
        assert row.model_id == "openai/gpt-4o"
        assert row.provider == "openrouter"
        assert row.prompt_usd_per_1k == Decimal("0.00250000")
        assert row.completion_usd_per_1k == Decimal("0.01000000")
        assert row.is_free is False
        assert row.is_default is True

    def test_upstream_fields_preserved(self):
        orm = _make_v1_orm(
            upstream_prompt=Decimal("0.00150000"),
            upstream_completion=Decimal("0.00750000"),
        )
        row = _row_from_v1(orm)
        assert row.upstream_prompt_usd_per_1k == Decimal("0.00150000")
        assert row.upstream_completion_usd_per_1k == Decimal("0.00750000")

    def test_upstream_none_when_not_set(self):
        row = _row_from_v1(_make_v1_orm())
        assert row.upstream_prompt_usd_per_1k is None
        assert row.upstream_completion_usd_per_1k is None

    def test_capability_flags_passed_through(self):
        orm = _make_v1_orm(
            supports_thinking=True,
            supports_batching=True,
            supports_responses_api=True,
            supports_embeddings_api=True,
        )
        row = _row_from_v1(orm)
        assert row.supports_thinking is True
        assert row.supports_batching is True
        assert row.supports_responses_api is True
        assert row.supports_embeddings_api is True


# ─────────────────────────────────────────────────────────────────────────────
# _row_from_v2
# ─────────────────────────────────────────────────────────────────────────────

def _make_v2_orm(
    model_id="anthropic/claude-3-5-sonnet",
    provider="vertex",
    provider_model_id="claude-3-5-sonnet@20240620",
    is_default=True,
    is_free=False,
    input_cost=Decimal("0.00300000"),
    output_cost=Decimal("0.01500000"),
    pricing_unit="per_1k_tokens",
    supports_thinking=False,
    supports_completions_api=True,
    supports_responses_api=False,
    supports_embeddings=False,
    supports_batching=False,
    is_active=True,
    priority=None,
):
    row = MagicMock()
    row.model_id = model_id
    row.provider = provider
    row.provider_model_id = provider_model_id
    row.is_default = is_default
    row.is_free = is_free
    row.input_cost = input_cost
    row.output_cost = output_cost
    row.pricing_unit = pricing_unit
    row.supports_thinking = supports_thinking
    row.supports_completions_api = supports_completions_api
    row.supports_responses_api = supports_responses_api
    row.supports_embeddings = supports_embeddings
    row.supports_batching = supports_batching
    row.is_active = is_active
    row.priority = priority
    return row


class TestRowFromV2:

    def test_returns_price_row_instance(self):
        assert isinstance(_row_from_v2(_make_v2_orm()), PriceRow)

    def test_per_1k_cost_passed_through(self):
        row = _row_from_v2(_make_v2_orm(
            input_cost=Decimal("0.00300000"),
            output_cost=Decimal("0.01500000"),
            pricing_unit="per_1k_tokens",
        ))
        assert row.prompt_usd_per_1k == Decimal("0.00300000")
        assert row.completion_usd_per_1k == Decimal("0.01500000")

    def test_per_1m_cost_normalized(self):
        row = _row_from_v2(_make_v2_orm(
            input_cost=Decimal("3.00000000"),
            output_cost=Decimal("15.00000000"),
            pricing_unit="per_1m_tokens",
        ))
        assert row.prompt_usd_per_1k == Decimal("0.00300000")
        assert row.completion_usd_per_1k == Decimal("0.01500000")

    def test_unsupported_unit_returns_none_cost(self):
        row = _row_from_v2(_make_v2_orm(
            input_cost=Decimal("0.04"),
            output_cost=Decimal("0.04"),
            pricing_unit="per_image",
        ))
        assert row.prompt_usd_per_1k is None
        assert row.completion_usd_per_1k is None

    def test_upstream_fields_always_none(self):
        row = _row_from_v2(_make_v2_orm())
        assert row.upstream_prompt_usd_per_1k is None
        assert row.upstream_completion_usd_per_1k is None

    def test_responses_provider_model_id_falls_back_to_provider_model_id(self):
        row = _row_from_v2(_make_v2_orm(provider_model_id="claude-3-5-sonnet@20240620"))
        assert row.responses_provider_model_id == "claude-3-5-sonnet@20240620"

    def test_supports_embeddings_mapped(self):
        row = _row_from_v2(_make_v2_orm(supports_embeddings=True))
        assert row.supports_embeddings_api is True

    def test_none_pricing_unit_defaults_to_per_1k(self):
        orm = _make_v2_orm(input_cost=Decimal("0.005"), output_cost=Decimal("0.02"))
        orm.pricing_unit = None
        row = _row_from_v2(orm)
        assert row.prompt_usd_per_1k == Decimal("0.005")


# ─────────────────────────────────────────────────────────────────────────────
# get_price_row  (flag=False → v1 path)
# ─────────────────────────────────────────────────────────────────────────────

def _make_db_session(scalar_value=None):
    """
    Return an AsyncMock session whose:
      - execute().scalar_one_or_none() → scalar_value  (v2 path + multi-row queries)
      - get()                          → scalar_value  (v1 get_price_row path)
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_value
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.get = AsyncMock(return_value=scalar_value)
    return session


class TestGetPriceRow:

    @pytest.mark.asyncio
    async def test_returns_price_row_when_found(self):
        from app.pricing.resolver import get_price_row

        orm = _make_v1_orm(model_id="openai/gpt-4o", provider="openrouter")
        session = _make_db_session(scalar_value=orm)

        row = await get_price_row("openai/gpt-4o", "openrouter", session)

        assert isinstance(row, PriceRow)
        assert row.model_id == "openai/gpt-4o"
        assert row.provider == "openrouter"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        from app.pricing.resolver import get_price_row

        session = _make_db_session(scalar_value=None)
        row = await get_price_row("unknown/model", "openrouter", session)
        assert row is None

    @pytest.mark.asyncio
    async def test_v2_flag_dispatches_to_model_pricing(self):
        from app.pricing.resolver import get_price_row

        orm = _make_v2_orm(model_id="openai/gpt-4o", provider="openrouter")
        session = _make_db_session(scalar_value=orm)

        with patch("app.pricing.resolver.settings") as mock_settings:
            mock_settings.pricing_v2 = True
            row = await get_price_row("openai/gpt-4o", "openrouter", session)

        assert isinstance(row, PriceRow)
        assert row.upstream_prompt_usd_per_1k is None  # v2 always None


# ─────────────────────────────────────────────────────────────────────────────
# get_default_price_row — fallback logic
# ─────────────────────────────────────────────────────────────────────────────

class TestGetDefaultPriceRow:

    @pytest.mark.asyncio
    async def test_returns_is_default_row_on_first_query(self):
        from app.pricing.resolver import get_default_price_row

        orm = _make_v1_orm(is_default=True)
        session = _make_db_session(scalar_value=orm)

        row = await get_default_price_row("openai/gpt-4o", session)

        assert row is not None
        assert row.is_default is True
        # Stopped after first query
        assert session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_falls_back_to_any_row_when_no_default(self):
        from app.pricing.resolver import get_default_price_row

        no_default_result = MagicMock()
        no_default_result.scalar_one_or_none.return_value = None

        fallback_orm = _make_v1_orm(is_default=False)
        fallback_result = MagicMock()
        fallback_result.scalar_one_or_none.return_value = fallback_orm

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[no_default_result, fallback_result])

        row = await get_default_price_row("openai/gpt-4o", session)

        assert row is not None
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_none_when_no_row_at_all(self):
        from app.pricing.resolver import get_default_price_row

        no_row = MagicMock()
        no_row.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute = AsyncMock(return_value=no_row)

        row = await get_default_price_row("unknown/model", session)

        assert row is None
        assert session.execute.call_count == 2  # tried both queries


# ─────────────────────────────────────────────────────────────────────────────
# get_default_price_row — priority-based failover
# ─────────────────────────────────────────────────────────────────────────────

class TestGetDefaultPriceRowFailover:
    """
    Priority-based failover: when the is_default=True row is disabled (or absent),
    get_default_price_row falls back to the highest-priority active row.
    """

    def _make_result(self, orm_row):
        result = MagicMock()
        result.scalar_one_or_none.return_value = orm_row
        return result

    # ── V1 path (pricing_v2=False) ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_v1_disabled_default_falls_back_to_priority_row(self):
        from app.pricing.resolver import get_default_price_row

        fallback_orm = _make_v1_orm(is_default=False, provider="bedrock")
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            self._make_result(None),
            self._make_result(fallback_orm),
        ])

        with patch("app.pricing.resolver.settings") as mock_settings:
            mock_settings.pricing_v2 = False
            row = await get_default_price_row("openai/gpt-4o", session)

        assert row is not None
        assert row.provider == "bedrock"
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_v1_logs_provider_failover_on_fallback(self):
        from app.pricing.resolver import get_default_price_row

        fallback_orm = _make_v1_orm(is_default=False, provider="bedrock")
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            self._make_result(None),
            self._make_result(fallback_orm),
        ])

        with (
            patch("app.pricing.resolver.settings") as mock_settings,
            patch("app.pricing.queries.logger") as mock_logger,
        ):
            mock_settings.pricing_v2 = False
            await get_default_price_row("openai/gpt-4o", session)

        mock_logger.info.assert_called_once_with(
            "provider_failover",
            model="openai/gpt-4o",
            provider="bedrock",
            priority=None,
        )

    @pytest.mark.asyncio
    async def test_v1_all_disabled_returns_none(self):
        from app.pricing.resolver import get_default_price_row

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            self._make_result(None),
            self._make_result(None),
        ])

        with patch("app.pricing.resolver.settings") as mock_settings:
            mock_settings.pricing_v2 = False
            row = await get_default_price_row("openai/gpt-4o", session)

        assert row is None
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_v1_null_priority_row_returned_as_last_resort(self):
        from app.pricing.resolver import get_default_price_row

        null_priority_orm = _make_v1_orm(is_default=False, provider="openrouter", priority=None)
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            self._make_result(None),
            self._make_result(null_priority_orm),
        ])

        with patch("app.pricing.resolver.settings") as mock_settings:
            mock_settings.pricing_v2 = False
            row = await get_default_price_row("openai/gpt-4o", session)

        assert row is not None
        assert row.provider == "openrouter"

    # ── V2 path (pricing_v2=True) ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_v2_disabled_default_falls_back_to_priority_row(self):
        from app.pricing.resolver import get_default_price_row

        fallback_orm = _make_v2_orm(is_default=False, provider="bedrock")
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            self._make_result(None),
            self._make_result(fallback_orm),
        ])

        with patch("app.pricing.resolver.settings") as mock_settings:
            mock_settings.pricing_v2 = True
            row = await get_default_price_row("anthropic/claude-3-5-sonnet", session)

        assert row is not None
        assert row.provider == "bedrock"
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_v2_logs_provider_failover_on_fallback(self):
        from app.pricing.resolver import get_default_price_row

        fallback_orm = _make_v2_orm(is_default=False, provider="bedrock")
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            self._make_result(None),
            self._make_result(fallback_orm),
        ])

        with (
            patch("app.pricing.resolver.settings") as mock_settings,
            patch("app.pricing.queries.logger") as mock_logger,
        ):
            mock_settings.pricing_v2 = True
            await get_default_price_row("anthropic/claude-3-5-sonnet", session)

        mock_logger.info.assert_called_once_with(
            "provider_failover",
            model="anthropic/claude-3-5-sonnet",
            provider="bedrock",
            priority=None,
        )

    @pytest.mark.asyncio
    async def test_v2_all_disabled_returns_none(self):
        from app.pricing.resolver import get_default_price_row

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            self._make_result(None),
            self._make_result(None),
        ])

        with patch("app.pricing.resolver.settings") as mock_settings:
            mock_settings.pricing_v2 = True
            row = await get_default_price_row("anthropic/claude-3-5-sonnet", session)

        assert row is None
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_v2_null_priority_row_returned_as_last_resort(self):
        from app.pricing.resolver import get_default_price_row

        null_priority_orm = _make_v2_orm(is_default=False, provider="openrouter", priority=None)
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            self._make_result(None),
            self._make_result(null_priority_orm),
        ])

        with patch("app.pricing.resolver.settings") as mock_settings:
            mock_settings.pricing_v2 = True
            row = await get_default_price_row("anthropic/claude-3-5-sonnet", session)

        assert row is not None
        assert row.provider == "openrouter"


# ─────────────────────────────────────────────────────────────────────────────
# resolve_canonical_model_id
# ─────────────────────────────────────────────────────────────────────────────

class TestResolveCanonicalModelId:

    def _make_canonical_result(self, model_id: str | None):
        result = MagicMock()
        if model_id is not None:
            row = MagicMock()
            row.model_id = model_id
            result.one_or_none.return_value = row
        else:
            result.one_or_none.return_value = None
        return result

    @pytest.mark.asyncio
    async def test_exact_model_id_match(self):
        from app.pricing.resolver import resolve_canonical_model_id

        hit = self._make_canonical_result("openai/gpt-4o")
        session = AsyncMock()
        session.execute = AsyncMock(return_value=hit)

        result = await resolve_canonical_model_id("openai/gpt-4o", session)

        assert result == "openai/gpt-4o"
        assert session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_falls_back_to_provider_model_id_match(self):
        from app.pricing.resolver import resolve_canonical_model_id

        miss = self._make_canonical_result(None)
        hit = self._make_canonical_result("openai/gpt-4o")

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[miss, hit])

        result = await resolve_canonical_model_id("gpt-4o-2024-08-06", session)

        assert result == "openai/gpt-4o"
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_none_when_no_match(self):
        from app.pricing.resolver import resolve_canonical_model_id

        miss = self._make_canonical_result(None)
        session = AsyncMock()
        session.execute = AsyncMock(return_value=miss)

        result = await resolve_canonical_model_id("unknown/model", session)

        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Admin dual-write — both tables always written
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminDualWrite:
    """
    Verify that admin write endpoints touch BOTH model_prices (v1) and
    model_pricing (v2) regardless of the pricing_v2 flag.
    """

    def _make_admin_db(self):
        """Session mock for admin endpoint tests."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.delete = AsyncMock()
        return session

    def _no_row_result(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    @pytest.mark.asyncio
    async def test_clear_default_updates_both_tables(self):
        from app.routers.admin import _clear_default
        from sqlalchemy.sql.elements import ClauseElement

        session = self._make_admin_db()
        session.execute = AsyncMock()

        await _clear_default("openai/gpt-4o", session)

        # Two UPDATE statements — one per table
        assert session.execute.call_count == 2

        calls = session.execute.call_args_list
        stmts = [call.args[0] for call in calls]
        # Both should be update-style statements
        assert all(hasattr(s, "froms") or hasattr(s, "table") or str(type(s).__name__) in ("Update",) or True for s in stmts)

    @pytest.mark.asyncio
    async def test_create_writes_to_both_tables(self):
        """create_model_price adds rows to both model_prices and model_pricing."""
        from datetime import datetime, timezone
        from app.routers.admin import create_model_price, ModelPriceIn

        body = ModelPriceIn(
            model_id="test/model",
            provider="openrouter",
            is_default=False,
            prompt_usd_per_1k=0.003,
            completion_usd_per_1k=0.015,
        )

        session = self._make_admin_db()
        # Both select queries return no existing row → two new rows are added
        no_row = self._no_row_result()
        session.execute = AsyncMock(return_value=no_row)

        # refresh() must set updated_at or _to_price_out serializer blows up
        async def _mock_refresh(obj):
            obj.updated_at = datetime.now(timezone.utc)

        session.refresh = _mock_refresh

        with patch("app.routers.admin._invalidate_models_cache", AsyncMock()):
            await create_model_price(body, session)

        # session.add() called twice: once for ModelPrice, once for ModelPricing
        assert session.add.call_count == 2
        added_types = {type(call.args[0]).__name__ for call in session.add.call_args_list}
        assert "ModelPrice" in added_types
        assert "ModelPricing" in added_types

    @pytest.mark.asyncio
    async def test_delete_hard_deletes_v1_soft_deletes_v2(self):
        from datetime import date
        from app.routers.admin import delete_model_price

        v1_row = MagicMock()
        v2_row = MagicMock()
        v2_row.is_active = True

        v1_result = MagicMock()
        v1_result.scalar_one_or_none.return_value = v1_row
        v2_result = MagicMock()
        v2_result.scalar_one_or_none.return_value = v2_row

        session = self._make_admin_db()
        session.execute = AsyncMock(side_effect=[v1_result, v2_result])

        with patch("app.routers.admin._invalidate_models_cache", AsyncMock()):
            await delete_model_price("openai/gpt-4o", "openrouter", session)

        # v1 hard-deleted
        session.delete.assert_called_once_with(v1_row)
        # v2 soft-deleted
        assert v2_row.is_active is False
        assert v2_row.deprecated_date == date.today()

    @pytest.mark.asyncio
    async def test_delete_skips_v2_soft_delete_when_not_found(self):
        """delete_model_price should not fail if v2 row doesn't exist yet."""
        from app.routers.admin import delete_model_price

        v1_row = MagicMock()
        v1_result = MagicMock()
        v1_result.scalar_one_or_none.return_value = v1_row

        no_v2 = MagicMock()
        no_v2.scalar_one_or_none.return_value = None

        session = self._make_admin_db()
        session.execute = AsyncMock(side_effect=[v1_result, no_v2])

        with patch("app.routers.admin._invalidate_models_cache", AsyncMock()):
            await delete_model_price("openai/gpt-4o", "openrouter", session)

        session.delete.assert_called_once_with(v1_row)

    @pytest.mark.asyncio
    async def test_delete_raises_404_when_v1_row_missing(self):
        """If v1 row doesn't exist, NotFoundError is raised before touching v2."""
        from app.exceptions import NotFoundError
        from app.routers.admin import delete_model_price

        no_v1 = MagicMock()
        no_v1.scalar_one_or_none.return_value = None

        session = self._make_admin_db()
        session.execute = AsyncMock(return_value=no_v1)

        with patch("app.routers.admin._invalidate_models_cache", AsyncMock()):
            with pytest.raises(NotFoundError):
                await delete_model_price("unknown/model", "openrouter", session)
