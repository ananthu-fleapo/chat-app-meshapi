"""
Raw SQLAlchemy queries for the pricing tables.

Returns ORM objects only — no PriceRow conversion happens here.
All functions accept an AsyncSession and are private (underscore-prefixed);
only resolver.py should call them.

Lazy model imports are preserved inside each function to avoid circular imports.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


# ── V1 queries (model_prices) ─────────────────────────────────────────────────


async def _fetch_price_row_v1(model_id: str, provider: str, db: AsyncSession):
    from app.db.models import ModelPrice

    return await db.get(ModelPrice, (model_id, provider))


async def _fetch_price_row_v2(model_id: str, provider: str, db: AsyncSession):
    from app.db.models import ModelPricing

    result = await db.execute(
        select(ModelPricing).where(
            ModelPricing.model_id == model_id,
            ModelPricing.provider == provider,
            ModelPricing.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


# ── Default-row queries (with priority fallback) ──────────────────────────────


async def _fetch_default_price_row_v1(model_id: str, db: AsyncSession):
    from app.db.models import ModelPrice

    result = await db.execute(
        select(ModelPrice)
        .where(
            ModelPrice.model_id == model_id,
            ModelPrice.is_default.is_(True),
            ModelPrice.is_active.is_(True),
        )
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    result = await db.execute(
        select(ModelPrice)
        .where(
            ModelPrice.model_id == model_id,
            ModelPrice.is_active.is_(True),
        )
        .order_by(ModelPrice.priority.asc().nulls_last())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        logger.info(
            "provider_failover", model=model_id, provider=row.provider, priority=row.priority
        )
    return row


async def _fetch_default_price_row_v2(model_id: str, db: AsyncSession):
    from app.db.models import ModelPricing

    result = await db.execute(
        select(ModelPricing)
        .where(
            ModelPricing.model_id == model_id,
            ModelPricing.is_default.is_(True),
            ModelPricing.is_active.is_(True),
        )
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    result = await db.execute(
        select(ModelPricing)
        .where(
            ModelPricing.model_id == model_id,
            ModelPricing.is_active.is_(True),
        )
        .order_by(ModelPricing.priority.asc().nulls_last())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        logger.info(
            "provider_failover", model=model_id, provider=row.provider, priority=row.priority
        )
    return row


# ── All-provider-rows queries ─────────────────────────────────────────────────


async def _fetch_all_provider_rows_v1(model_id: str, db: AsyncSession):
    from app.db.models import ModelPrice

    result = await db.execute(select(ModelPrice).where(ModelPrice.model_id == model_id))
    return list(result.scalars().all())


async def _fetch_all_provider_rows_v2(model_id: str, db: AsyncSession):
    from app.db.models import ModelPricing

    result = await db.execute(
        select(ModelPricing).where(
            ModelPricing.model_id == model_id,
            ModelPricing.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


# ── List-default-rows queries (Model × price join) ────────────────────────────


async def _list_default_price_rows_v1(db: AsyncSession):
    from app.db.models import Model, ModelPrice

    result = await db.execute(
        select(Model, ModelPrice)
        .join(
            ModelPrice,
            (ModelPrice.model_id == Model.model_id) & ModelPrice.is_default.is_(True),
        )
        .where(Model.is_enabled.is_(True))
        .order_by(Model.model_id)
    )
    return list(result.all())


async def _list_default_price_rows_v2(db: AsyncSession):
    from app.db.models import Model, ModelPricing

    result = await db.execute(
        select(Model, ModelPricing)
        .join(
            ModelPricing,
            (ModelPricing.model_id == Model.model_id)
            & ModelPricing.is_default.is_(True)
            & ModelPricing.is_active.is_(True),
        )
        .where(Model.is_enabled.is_(True))
        .order_by(Model.model_id)
    )
    return list(result.all())


# ── Canonical model-id resolution queries ─────────────────────────────────────


async def _resolve_canonical_model_id_v1(raw_model: str, db: AsyncSession) -> str | None:
    from app.db.models import Model, ModelPrice

    result = await db.execute(
        select(ModelPrice.model_id)
        .join(Model, Model.model_id == ModelPrice.model_id)
        .where(ModelPrice.model_id == raw_model, Model.is_enabled.is_(True))
        .limit(1)
    )
    row = result.one_or_none()
    if row is not None:
        return row.model_id

    result = await db.execute(
        select(ModelPrice.model_id)
        .join(Model, Model.model_id == ModelPrice.model_id)
        .where(ModelPrice.provider_model_id == raw_model, Model.is_enabled.is_(True))
        .limit(1)
    )
    row = result.one_or_none()
    return row.model_id if row is not None else None


async def _resolve_canonical_model_id_v2(raw_model: str, db: AsyncSession) -> str | None:
    from app.db.models import Model, ModelPricing

    result = await db.execute(
        select(ModelPricing.model_id)
        .join(Model, Model.model_id == ModelPricing.model_id)
        .where(
            ModelPricing.model_id == raw_model,
            ModelPricing.is_active.is_(True),
            Model.is_enabled.is_(True),
        )
        .limit(1)
    )
    row = result.one_or_none()
    if row is not None:
        return row.model_id

    result = await db.execute(
        select(ModelPricing.model_id)
        .join(Model, Model.model_id == ModelPricing.model_id)
        .where(
            ModelPricing.provider_model_id == raw_model,
            ModelPricing.is_active.is_(True),
            Model.is_enabled.is_(True),
        )
        .limit(1)
    )
    row = result.one_or_none()
    return row.model_id if row is not None else None


# ── List-all-provider-rows queries (Model × price outer join) ─────────────────


async def _list_all_provider_rows_v1(db: AsyncSession):
    from app.db.models import Model, ModelPrice

    result = await db.execute(
        select(Model, ModelPrice)
        .outerjoin(ModelPrice, Model.model_id == ModelPrice.model_id)
        .where(Model.is_enabled.is_(True))
        .order_by(Model.model_id, ModelPrice.provider)
    )
    return list(result.all())


async def _list_all_provider_rows_v2(db: AsyncSession):
    from app.db.models import Model, ModelPricing

    result = await db.execute(
        select(Model, ModelPricing)
        .outerjoin(
            ModelPricing,
            (ModelPricing.model_id == Model.model_id) & ModelPricing.is_active.is_(True),
        )
        .where(Model.is_enabled.is_(True))
        .order_by(Model.model_id, ModelPricing.provider)
    )
    return list(result.all())
