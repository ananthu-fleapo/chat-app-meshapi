"""
Pricing resolver — feature-flagged abstraction over model_prices (v1) and
model_pricing (v2).

All call sites that previously queried ModelPrice directly should import from
here instead.  The flag settings.pricing_v2 determines which table is read;
all functions return PriceRow, a common dataclass that mirrors ModelPrice's
interface so callers need no change beyond the import swap.

V2 pricing unit normalization
------------------------------
All costs are normalised to "per 1 000 tokens" regardless of the pricing_unit
stored in model_pricing:
  per_1k_tokens  → use cost as-is
  per_1m_tokens  → divide by 1 000
  other units    → None (callers treat None as "no price configured")

V2 upstream cost
-----------------
model_pricing has no upstream price columns; upstream_prompt_usd_per_1k and
upstream_completion_usd_per_1k are always None when pricing_v2 is True.

V2 responses_provider_model_id
--------------------------------
model_pricing has no separate responses column; the same provider_model_id is
used for both the completions and responses API paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.pricing import queries

# Pricing units whose costs map directly to "per 1k tokens"
_PER_1K = "per_1k_tokens"
_PER_1M = "per_1m_tokens"


@dataclass
class PriceRow:
    """
    Normalised view of a single (model_id, provider) pricing entry.

    Regardless of which underlying table is read, callers receive a consistent
    object with the same fields as the legacy ModelPrice ORM row.
    """

    model_id: str
    provider: str
    provider_model_id: str | None
    responses_provider_model_id: str | None
    is_default: bool
    is_free: bool
    prompt_usd_per_1k: Decimal | None
    completion_usd_per_1k: Decimal | None
    upstream_prompt_usd_per_1k: Decimal | None
    upstream_completion_usd_per_1k: Decimal | None
    supports_thinking: bool
    supports_completions_api: bool
    supports_responses_api: bool
    supports_embeddings_api: bool
    supports_batching: bool


# ── V1 helpers (read model_prices) ────────────────────────────────────────────


def _row_from_v1(mp) -> PriceRow:
    return PriceRow(
        model_id=mp.model_id,
        provider=mp.provider,
        provider_model_id=mp.provider_model_id,
        responses_provider_model_id=mp.responses_provider_model_id,
        is_default=mp.is_default,
        is_free=mp.is_free,
        prompt_usd_per_1k=mp.prompt_usd_per_1k,
        completion_usd_per_1k=mp.completion_usd_per_1k,
        upstream_prompt_usd_per_1k=mp.upstream_prompt_usd_per_1k,
        upstream_completion_usd_per_1k=mp.upstream_completion_usd_per_1k,
        supports_thinking=mp.supports_thinking,
        supports_completions_api=mp.supports_completions_api,
        supports_responses_api=mp.supports_responses_api,
        supports_embeddings_api=mp.supports_embeddings_api,
        supports_batching=mp.supports_batching,
    )


# ── V2 helpers (read model_pricing) ───────────────────────────────────────────


def _normalise_cost(cost: Decimal | None, unit: str) -> Decimal | None:
    """Convert cost to per-1k-tokens equivalent, or None for non-token units."""
    if cost is None:
        return None
    if unit == _PER_1K:
        return cost
    if unit == _PER_1M:
        return cost / 1000
    return None  # per_image, per_second, etc. — not representable as per-1k


def _row_from_v2(mp) -> PriceRow:
    unit = mp.pricing_unit or _PER_1K
    return PriceRow(
        model_id=mp.model_id,
        provider=mp.provider,
        provider_model_id=mp.provider_model_id,
        responses_provider_model_id=mp.provider_model_id,  # fall back to same ID
        is_default=mp.is_default,
        is_free=mp.is_free,
        prompt_usd_per_1k=_normalise_cost(mp.input_cost, unit),
        completion_usd_per_1k=_normalise_cost(mp.output_cost, unit),
        upstream_prompt_usd_per_1k=None,
        upstream_completion_usd_per_1k=None,
        supports_thinking=mp.supports_thinking,
        supports_completions_api=mp.supports_completions_api,
        supports_responses_api=mp.supports_responses_api,
        supports_embeddings_api=mp.supports_embeddings,
        supports_batching=mp.supports_batching,
    )


# ── Public API ────────────────────────────────────────────────────────────────


async def get_price_row(model_id: str, provider: str, db: AsyncSession) -> PriceRow | None:
    """Return the price row for an exact (model_id, provider) pair."""
    if settings.pricing_v2:
        row = await queries._fetch_price_row_v2(model_id, provider, db)
        return _row_from_v2(row) if row is not None else None
    else:
        row = await queries._fetch_price_row_v1(model_id, provider, db)
        return _row_from_v1(row) if row is not None else None


async def get_default_price_row(model_id: str, db: AsyncSession) -> PriceRow | None:
    """
    Return the is_default=True price row for model_id.

    Falls back to any row for this model when no default is set (mirrors the
    existing behaviour in balance.py / registry.py).
    """
    if settings.pricing_v2:
        row = await queries._fetch_default_price_row_v2(model_id, db)
        return _row_from_v2(row) if row is not None else None
    else:
        row = await queries._fetch_default_price_row_v1(model_id, db)
        return _row_from_v1(row) if row is not None else None


async def get_all_provider_price_rows(model_id: str, db: AsyncSession) -> list[PriceRow]:
    """Return all (model_id, provider) price rows — used by model health checks."""
    if settings.pricing_v2:
        rows = await queries._fetch_all_provider_rows_v2(model_id, db)
        return [_row_from_v2(r) for r in rows]
    else:
        rows = await queries._fetch_all_provider_rows_v1(model_id, db)
        return [_row_from_v1(r) for r in rows]


async def list_default_price_rows(db: AsyncSession) -> list[tuple]:
    """
    Return (Model, PriceRow) pairs for all enabled models with a default price.

    Used by GET /v1/models to build the model listing.
    """
    if settings.pricing_v2:
        pairs = await queries._list_default_price_rows_v2(db)
        return [(m, _row_from_v2(mp)) for m, mp in pairs]
    else:
        pairs = await queries._list_default_price_rows_v1(db)
        return [(m, _row_from_v1(mp)) for m, mp in pairs]


async def resolve_canonical_model_id(raw_model: str, db: AsyncSession) -> str | None:
    """
    Resolve a raw model string to the canonical model_id stored in the price table.

    Lookup order (both v1 and v2):
      1. Exact model_id match  (e.g. "openai/gpt-4o-mini")
      2. provider_model_id match  (e.g. "gpt-4o-mini-2024-07-18")
    Both paths require models.is_enabled=True.

    Returns None when no match is found (caller should raise UnsupportedModelError).
    """
    if settings.pricing_v2:
        return await queries._resolve_canonical_model_id_v2(raw_model, db)
    else:
        return await queries._resolve_canonical_model_id_v1(raw_model, db)


async def list_all_provider_price_rows(db: AsyncSession) -> list[tuple]:
    """
    Return (Model, PriceRow | None) for every enabled model × every provider row.

    Used by the model health check runner. Models with no price row yield a
    single (Model, None) tuple so the health check still includes them with
    default capabilities (completions=True, others=False).

    Routes to model_prices or model_pricing based on settings.pricing_v2.
    """
    if settings.pricing_v2:
        pairs = await queries._list_all_provider_rows_v2(db)
        return [(m, _row_from_v2(mp) if mp is not None else None) for m, mp in pairs]
    else:
        pairs = await queries._list_all_provider_rows_v1(db)
        return [(m, _row_from_v1(mp) if mp is not None else None) for m, mp in pairs]


async def resolve_routing_from_price(
    model_id: str, db: AsyncSession
) -> tuple[str, str | None, str | None] | None:
    """
    Return (provider, provider_model_id, responses_provider_model_id) for the
    default price row, or None when no row exists.

    Mirrors the structure returned by registry.resolve_routing().
    """
    row = await get_default_price_row(model_id, db)
    if row is None:
        return None
    return row.provider, row.provider_model_id, row.responses_provider_model_id
