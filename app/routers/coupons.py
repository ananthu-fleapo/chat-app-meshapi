from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.control_plane import ControlPlaneIdentity, get_admin_user, get_control_plane_user
from app.auth.dependencies import verify_webhook_key
from app.config import settings
from app.db.models import CheckoutCoupon, CouponSyncIssue, CouponUser, PaymentEvent
from app.db.session import get_db_session
from app.payments import stripe_client

from .coupon_utils import _normalize_coupon_code, _normalize_user_ids

router = APIRouter(tags=["coupons"])
logger = structlog.get_logger()


# ── Public schemas ────────────────────────────────────────────────────────────


class PublicCouponSummary(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None
    discount_type: str
    discount_value: str
    discount_amount: str | None = None
    valid_till: str | None = None
    is_active: bool
    max_uses: int | None = None
    used_count: int
    reuse_policy: str
    currency: str


class CouponSummary(PublicCouponSummary):
    user_ids: list[str]
    stripe_synced_at: str | None = None
    stripe_coupon_id: str | None = None


class CouponValidateRequest(BaseModel):
    code: str
    amount: Decimal
    currency: str


class CouponValidateResponse(BaseModel):
    valid: bool
    discount_type: str | None = None
    discount_value: str | None = None
    discount_amount: str | None = None


class AdminCouponCreateRequest(BaseModel):
    code: str
    name: str
    description: str | None = None
    discount_type: Literal["percentage", "flat"]
    discount_value: Decimal
    currency: str = "INR"
    reuse_policy: Literal["single_use", "reusable"] = "single_use"
    max_uses: int | None = None
    valid_till: datetime | None = None
    is_active: bool = True
    user_ids: list[str] = Field(default_factory=list)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        normalized = v.strip().upper()
        if not normalized:
            raise ValueError("Coupon code cannot be empty")
        return normalized

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.strip().upper()


class AdminCouponUpdateRequest(BaseModel):
    """
    discount_type and discount_value are intentionally excluded — these fields come
    from the payment gateway (set during sync). Update them in the Stripe dashboard.
    """

    name: str | None = None
    description: str | None = None
    reuse_policy: Literal["single_use", "reusable"] | None = None
    max_uses: int | None = None
    valid_till: datetime | None = None
    is_active: bool | None = None
    user_ids: list[str] | None = None


class AssignCouponUsersRequest(BaseModel):
    user_ids: list[str] = Field(default_factory=list)


class CouponStatsOut(BaseModel):
    total: int
    active: int
    total_usage: int
    most_used: list[dict[str, Any]]


class ProviderSyncStatus(BaseModel):
    in_sync: bool
    mismatches: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class CouponSyncCheckResponse(BaseModel):
    stripe: ProviderSyncStatus


class SyncAllResponse(BaseModel):
    fetched: list[dict[str, Any]]
    imported: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    auto_deactivated: list[dict[str, Any]]


class SyncIssueOut(BaseModel):
    id: str
    coupon_id: str | None
    coupon_code: str
    provider: str
    issue_type: str
    details: dict[str, Any]
    status: str
    created_at: str
    resolved_at: str | None
    resolved_by: str | None


class SyncIssueUpdateRequest(BaseModel):
    status: Literal["resolved", "dismissed"]
    resolved_by: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _decimal_str(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _coupon_to_summary(
    coupon: CheckoutCoupon,
    discount_amount: Decimal | None = None,
    public: bool = False,
) -> PublicCouponSummary | CouponSummary:
    data: dict[str, Any] = {
        "id": str(coupon.id),
        "code": coupon.code,
        "name": coupon.name,
        "description": coupon.description,
        "discount_type": coupon.discount_type,
        "discount_value": _decimal_str(coupon.discount_value) or "0",
        "discount_amount": _decimal_str(discount_amount),
        "valid_till": coupon.valid_till.isoformat() if coupon.valid_till else None,
        "is_active": coupon.is_active,
        "max_uses": coupon.max_uses,
        "used_count": coupon.used_count or 0,
        "reuse_policy": coupon.reuse_policy,
        "currency": getattr(coupon, "currency", "INR"),
    }
    if not public:
        data["user_ids"] = (
            [u.user_id for u in coupon.users]
            if ("users" in coupon.__dict__ and coupon.users is not None)
            else []
        )
        data["stripe_synced_at"] = (
            coupon.stripe_synced_at.isoformat() if coupon.stripe_synced_at is not None else None
        )
        data["stripe_coupon_id"] = coupon.stripe_coupon_id
        return CouponSummary(**data)
    return PublicCouponSummary(**data)


async def _replace_coupon_users(
    db: AsyncSession,
    coupon_id: UUID,
    user_ids: list[str],
) -> set[str]:
    existing = await db.execute(select(CouponUser).where(CouponUser.coupon_id == coupon_id))
    rows = existing.scalars().all()
    current_ids = {row.user_id for row in rows}
    target_ids = set(user_ids)

    to_delete = [row for row in rows if row.user_id not in target_ids]
    to_add = [uid for uid in target_ids if uid not in current_ids]

    for row in to_delete:
        await db.delete(row)
    for user_id in to_add:
        db.add(CouponUser(coupon_id=coupon_id, user_id=user_id))

    return current_ids | target_ids


def _calculate_discount_amount(coupon: CheckoutCoupon, amount: Decimal) -> Decimal:
    if coupon.discount_type == "percentage":
        return (amount * coupon.discount_value / Decimal("100")).quantize(Decimal("0.01"))
    return min(amount, coupon.discount_value).quantize(Decimal("0.01"))


async def _get_coupon_for_user(
    db: AsyncSession,
    user_id: str,
    code: str,
    amount: Decimal | None = None,
) -> tuple[CheckoutCoupon, Decimal | None]:
    normalized_code = _normalize_coupon_code(code)
    if not normalized_code:
        raise HTTPException(status_code=404, detail="Coupon not found")
    result = await db.execute(
        select(CheckoutCoupon)
        .where(func.lower(CheckoutCoupon.code) == normalized_code.lower())
        .limit(1)
    )
    coupon = result.scalar_one_or_none()
    if coupon is None:
        raise HTTPException(status_code=404, detail="Coupon not found")
    if not coupon.is_active:
        raise HTTPException(status_code=422, detail="Coupon is inactive")
    if coupon.valid_till and coupon.valid_till < datetime.now(UTC):
        raise HTTPException(status_code=422, detail="Coupon has expired")
    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        raise HTTPException(status_code=409, detail="Coupon usage limit reached")

    targeting_count = await db.scalar(
        select(func.count()).select_from(CouponUser).where(CouponUser.coupon_id == coupon.id)
    )
    if targeting_count and targeting_count > 0:
        assignment = await db.execute(
            select(CouponUser)
            .where(CouponUser.coupon_id == coupon.id, CouponUser.user_id == user_id)
            .limit(1)
        )
        if assignment.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Coupon is not assigned to this user")

    if coupon.reuse_policy == "single_use":
        existing_usage = await db.execute(
            select(PaymentEvent)
            .where(PaymentEvent.user_id == user_id)
            .where(func.lower(PaymentEvent.coupon_code) == coupon.code.lower())
            .limit(1)
        )
        if existing_usage.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Coupon already used by this user")

    return coupon, (_calculate_discount_amount(coupon, amount) if amount is not None else None)


def _log_issue(
    db: AsyncSession,
    coupon: CheckoutCoupon,
    provider: str,
    issue_type: str,
    details: dict[str, Any],
) -> None:
    db.add(
        CouponSyncIssue(
            coupon_id=coupon.id,
            coupon_code=coupon.code,
            provider=provider,
            issue_type=issue_type,
            details=details,
        )
    )


def _issue_to_out(i: CouponSyncIssue) -> SyncIssueOut:
    return SyncIssueOut(
        id=str(i.id),
        coupon_id=str(i.coupon_id) if i.coupon_id else None,
        coupon_code=i.coupon_code,
        provider=i.provider,
        issue_type=i.issue_type,
        details=i.details or {},
        status=i.status,
        created_at=i.created_at.isoformat(),
        resolved_at=i.resolved_at.isoformat() if i.resolved_at else None,
        resolved_by=i.resolved_by,
    )


# ── Public endpoints ──────────────────────────────────────────────────────────


@router.get("/v1/coupons", response_model=list[PublicCouponSummary])
async def list_coupons(
    provider: str | None = None,
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    """
    List coupons available to the requesting user.

    Pass `?provider=stripe` to filter to coupons that exist in Stripe —
    the routersvc-client should pass the active PG so users only see coupons
    they can actually apply at checkout.
    """
    now = datetime.now(UTC)
    user_id = identity.sub

    stmt = (
        select(CheckoutCoupon)
        .where(CheckoutCoupon.is_active.is_(True))
        .where(or_(CheckoutCoupon.valid_till.is_(None), CheckoutCoupon.valid_till >= now))
        .where(
            or_(
                CheckoutCoupon.max_uses.is_(None),
                CheckoutCoupon.used_count < CheckoutCoupon.max_uses,
            )
        )
    )

    # Filter to coupons that exist in the requested payment gateway
    if provider == "stripe":
        stmt = stmt.where(CheckoutCoupon.stripe_synced_at.is_not(None))

    is_targeted = exists().where(CouponUser.coupon_id == CheckoutCoupon.id)
    is_targeted_to_me = exists().where(
        CouponUser.coupon_id == CheckoutCoupon.id,
        CouponUser.user_id == user_id,
    )
    stmt = stmt.where(or_(~is_targeted, is_targeted_to_me))

    has_used = exists().where(
        PaymentEvent.user_id == user_id,
        func.lower(PaymentEvent.coupon_code) == func.lower(CheckoutCoupon.code),
    )
    stmt = stmt.where(or_(CheckoutCoupon.reuse_policy != "single_use", ~has_used))
    stmt = stmt.order_by(CheckoutCoupon.discount_value.desc())

    result = await db.execute(stmt)
    coupons = result.scalars().all()
    return [_coupon_to_summary(c, public=True) for c in coupons]


@router.post("/v1/coupons/validate", response_model=CouponValidateResponse)
async def validate_coupon(
    body: CouponValidateRequest,
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    try:
        coupon, discount_amount = await _get_coupon_for_user(
            db, identity.sub, body.code, body.amount
        )
    except HTTPException:
        return CouponValidateResponse(valid=False)

    return CouponValidateResponse(
        valid=True,
        discount_type=coupon.discount_type,
        discount_value=_decimal_str(coupon.discount_value),
        discount_amount=_decimal_str(discount_amount),
    )


# ── Admin endpoints ───────────────────────────────────────────────────────────

admin_router = APIRouter(
    prefix="/v1/admin/coupons",
    tags=["admin-coupons"],
    dependencies=[Depends(get_admin_user)],
)


@admin_router.post("", response_model=CouponSummary, status_code=201)
async def create_coupon(body: AdminCouponCreateRequest, db: AsyncSession = Depends(get_db_session)):  # noqa: B008
    """
    Register a coupon locally. No call is made to Stripe.
    To link this coupon to Stripe, run sync-all after creating the coupon in Stripe dashboard.
    """
    existing = await db.execute(
        select(CheckoutCoupon)
        .where(func.lower(CheckoutCoupon.code) == (body.code or "").upper().strip())
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail=f"Coupon '{body.code}' already exists.")

    coupon = CheckoutCoupon(
        code=_normalize_coupon_code(body.code),
        name=body.name,
        description=body.description,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        currency=body.currency,
        reuse_policy=body.reuse_policy,
        max_uses=body.max_uses,
        valid_till=body.valid_till,
        is_active=body.is_active,
    )
    db.add(coupon)
    await db.flush()

    if body.user_ids is not None:
        await _replace_coupon_users(db, coupon.id, _normalize_user_ids(body.user_ids))

    await db.refresh(coupon, attribute_names=["users"])
    return _coupon_to_summary(coupon)


@admin_router.get("", response_model=list[CouponSummary])
async def list_admin_coupons(
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    stmt = select(CheckoutCoupon)
    if status == "active":
        stmt = stmt.where(CheckoutCoupon.is_active.is_(True))
    elif status == "inactive":
        stmt = stmt.where(CheckoutCoupon.is_active.is_(False))
    if search:
        needle = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(CheckoutCoupon.code).like(needle),
                func.lower(CheckoutCoupon.name).like(needle),
                func.lower(func.coalesce(CheckoutCoupon.description, "")).like(needle),
            )
        )
    stmt = stmt.options(selectinload(CheckoutCoupon.users))
    result = await db.execute(stmt.order_by(CheckoutCoupon.created_at.desc()))
    return [_coupon_to_summary(coupon) for coupon in result.scalars().all()]


@admin_router.patch("/{coupon_id}", response_model=CouponSummary)
async def update_coupon(
    coupon_id: UUID,
    body: AdminCouponUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    """
    Update local coupon metadata. No call is made to any payment gateway.
    discount_type and discount_value are managed by the PG and updated automatically
    on the next sync-all run.
    """
    stmt = (
        select(CheckoutCoupon)
        .where(CheckoutCoupon.id == coupon_id)
        .options(selectinload(CheckoutCoupon.users))
    )
    coupon = await db.scalar(stmt)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Coupon not found")

    payload = body.model_dump(exclude_unset=True)
    user_ids = payload.pop("user_ids", None)
    for field, value in payload.items():
        setattr(coupon, field, value)

    if user_ids is not None:
        await _replace_coupon_users(db, coupon.id, _normalize_user_ids(user_ids))

    await db.refresh(coupon, attribute_names=["users"])
    return _coupon_to_summary(coupon)


@admin_router.delete("/{coupon_id}")
async def delete_coupon(coupon_id: UUID, db: AsyncSession = Depends(get_db_session)):  # noqa: B008
    """
    Soft-delete locally (sets is_active=false). No call is made to Stripe.
    The coupon will remain active in Stripe until deactivated there manually.
    """
    coupon = await db.scalar(select(CheckoutCoupon).where(CheckoutCoupon.id == coupon_id))
    if coupon is None:
        raise HTTPException(status_code=404, detail="Coupon not found")
    coupon.is_active = False
    return {"deleted": True}


@admin_router.post("/{coupon_id}/users")
async def assign_coupon_users(
    coupon_id: UUID,
    body: AssignCouponUsersRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    coupon = await db.scalar(select(CheckoutCoupon).where(CheckoutCoupon.id == coupon_id))
    if coupon is None:
        raise HTTPException(status_code=404, detail="Coupon not found")
    await _replace_coupon_users(db, coupon_id, _normalize_user_ids(body.user_ids))
    return {"assigned": len(body.user_ids or [])}


@admin_router.get("/stats", response_model=CouponStatsOut)
async def coupon_stats(db: AsyncSession = Depends(get_db_session)):  # noqa: B008
    total = await db.scalar(select(func.count()).select_from(CheckoutCoupon)) or 0
    active = (
        await db.scalar(
            select(func.count())
            .select_from(CheckoutCoupon)
            .where(CheckoutCoupon.is_active.is_(True))
        )
        or 0
    )
    total_usage = (
        await db.scalar(
            select(func.coalesce(func.sum(CheckoutCoupon.used_count), 0)).select_from(
                CheckoutCoupon
            )
        )
        or 0
    )
    result = await db.execute(
        select(CheckoutCoupon).order_by(CheckoutCoupon.used_count.desc()).limit(5)
    )
    most_used = [{"code": c.code, "used_count": c.used_count} for c in result.scalars().all()]
    return CouponStatsOut(total=total, active=active, total_usage=total_usage, most_used=most_used)


@admin_router.post("/{coupon_id}/sync", response_model=CouponSyncCheckResponse)
async def sync_check_coupon(coupon_id: UUID, db: AsyncSession = Depends(get_db_session)):  # noqa: B008
    """
    Read-only diff — fetch current state from Stripe and compare field-by-field.
    No changes are made to local records or to Stripe.
    """
    coupon = await db.scalar(select(CheckoutCoupon).where(CheckoutCoupon.id == coupon_id))
    if coupon is None:
        raise HTTPException(status_code=404, detail="Coupon not found")

    stripe_enabled = bool(settings.stripe_api_key)

    stripe_result = await asyncio.gather(
        stripe_client.get_coupon(coupon.code) if stripe_enabled else asyncio.sleep(0, result=None),
        return_exceptions=True,
    )
    stripe_result = stripe_result[0]

    def _provider_status(remote: Any, compare_fn: Any) -> ProviderSyncStatus:
        if isinstance(remote, Exception):
            return ProviderSyncStatus(in_sync=False, error=str(remote))
        if remote is None:
            return ProviderSyncStatus(in_sync=False, error="Not found in provider")
        mismatches = compare_fn(coupon, remote)
        return ProviderSyncStatus(in_sync=len(mismatches) == 0, mismatches=mismatches)

    return CouponSyncCheckResponse(
        stripe=_provider_status(stripe_result, stripe_client.compare_coupon),
    )


@admin_router.post("/sync-all", response_model=SyncAllResponse)
async def sync_all_coupons(db: AsyncSession = Depends(get_db_session)):  # noqa: B008
    """
    Pull all coupons from Stripe; upsert into local DB.

    Rules:
    - Stripe data wins for discount fields (type, value, currency, max_uses, valid_till, is_active).
    - Local name / description are preserved if the admin has edited them after the last sync.
    - used_count is updated to max(local, stripe.times_redeemed) — never decreases.
    - If used_count >= max_uses after update, coupon is auto-deactivated locally.
    """
    stripe_enabled = bool(settings.stripe_api_key)
    now = datetime.now(UTC)

    logger.info(
        "coupon_sync_start",
        stripe_enabled=stripe_enabled,
        stripe_api_url=settings.stripe_api_url,
    )

    if not stripe_enabled:
        logger.warning(
            "coupon_sync_stripe_skipped",
            reason="STRIPE_API_KEY not set",
        )

    fetched: list[dict[str, Any]] = []
    imported: list[dict[str, Any]] = []
    errors_out: list[dict[str, Any]] = []
    auto_deactivated: list[dict[str, Any]] = []

    # ── Fetch from Stripe (coupons + promo codes in parallel) ────────────────
    stripe_raw: list[dict] = []
    promo_raw: list[dict] = []

    gather_results = await asyncio.gather(
        stripe_client.list_all_coupons() if stripe_enabled else asyncio.sleep(0, result=[]),
        stripe_client.list_all_promo_codes() if stripe_enabled else asyncio.sleep(0, result=[]),
        return_exceptions=True,
    )
    stripe_fetch, promo_fetch = gather_results[0], gather_results[1]

    if isinstance(stripe_fetch, BaseException):
        logger.error(
            "coupon_sync_stripe_fetch_failed", error=str(stripe_fetch), exc_info=stripe_fetch
        )
        errors_out.append(
            {"provider": "stripe", "error": f"Failed to list coupons: {stripe_fetch!s}"}
        )
    else:
        stripe_raw = stripe_fetch or []
        logger.info("coupon_sync_stripe_fetched", count=len(stripe_raw))

    if isinstance(promo_fetch, BaseException):
        logger.error("coupon_sync_promo_fetch_failed", error=str(promo_fetch), exc_info=promo_fetch)
        errors_out.append(
            {"provider": "stripe_promo", "error": f"Failed to list promo codes: {promo_fetch!s}"}
        )
    else:
        promo_raw = promo_fetch or []
        logger.info("coupon_sync_promo_fetched", count=len(promo_raw))

    # Build lookup map: Stripe coupon ID → Stripe dict
    stripe_by_code: dict[str, dict] = {c["id"]: c for c in stripe_raw}

    # ── Load all local coupons ────────────────────────────────────────────────
    result = await db.execute(select(CheckoutCoupon))
    local_coupons: list[CheckoutCoupon] = list(result.scalars().all())
    local_by_code: dict[str, CheckoutCoupon] = {c.code: c for c in local_coupons}

    logger.info("coupon_sync_local_loaded", local_count=len(local_coupons))

    # ── Process each local coupon against Stripe data ─────────────────────────
    for coupon in local_coupons:
        providers_fetched: list[str] = []

        if stripe_enabled:
            stripe_remote = stripe_by_code.get(coupon.code)
            if stripe_remote is not None:
                _apply_stripe_data(coupon, stripe_remote, now)
                providers_fetched.append("stripe")
            else:
                logger.debug("coupon_sync_stripe_not_found", code=coupon.code)

        if providers_fetched:
            fetched.append({"code": coupon.code, "providers": providers_fetched})

        # Auto-deactivate if used_count has reached max_uses
        if (
            coupon.is_active
            and coupon.max_uses is not None
            and (coupon.used_count or 0) >= coupon.max_uses
        ):
            logger.warning(
                "coupon_sync_auto_deactivated",
                code=coupon.code,
                used_count=coupon.used_count,
                max_uses=coupon.max_uses,
            )
            coupon.is_active = False
            _log_issue(
                db,
                coupon,
                "stripe",
                "auto_deactivated",
                {
                    "used_count": coupon.used_count,
                    "max_uses": coupon.max_uses,
                    "note": "Auto-deactivated locally. Deactivate in Stripe dashboard too.",
                },
            )
            auto_deactivated.append(
                {
                    "code": coupon.code,
                    "used_count": coupon.used_count,
                    "max_uses": coupon.max_uses,
                }
            )

    # ── Deactivate existing coupon-level rows (Stripe coupon IDs stored as code) ──
    # Stripe coupons are discount templates — the user-facing redemption strings are
    # always promo codes. Any coupon-level row (stripe_coupon_id == code) that is still
    # active should be deactivated; customers should redeem via a promo code instead.
    for coupon in local_coupons:
        if (
            coupon.is_active
            and coupon.stripe_coupon_id is not None
            and coupon.stripe_coupon_id == coupon.code  # coupon-level row, not a promo row
        ):
            coupon.is_active = False
            auto_deactivated.append({"code": coupon.code, "reason": "coupon_level_row_replaced"})
            logger.info("coupon_sync_deactivated_coupon_level_row", code=coupon.code)

    # Stripe coupon-level rows are never created by sync — only promo code rows are.
    # Stripe coupons are templates; the promo code sync below creates the actual rows.

    # ── Sync Stripe promotion codes ───────────────────────────────────────────
    for promo in promo_raw:
        coupon_data: dict = promo.get("coupon", {})
        parent_stripe_id: str = coupon_data.get("id", "")
        promo_code_str: str = promo.get("code", "")
        if not parent_stripe_id or not promo_code_str:
            continue
        existing = local_by_code.get(promo_code_str)
        if existing is not None:
            _apply_stripe_promo_data(existing, promo, coupon_data, now)
            fetched.append({"code": promo_code_str, "providers": ["stripe_promo"]})
        else:
            try:
                new_promo_row = _promo_code_from_stripe(promo, now)
                db.add(new_promo_row)
                await db.flush()
                local_by_code[promo_code_str] = new_promo_row
                imported.append({"code": promo_code_str, "from": "stripe_promo"})
                logger.info("coupon_sync_promo_imported", code=promo_code_str)
            except Exception as exc:  # noqa: BLE001
                logger.error("coupon_sync_promo_import_failed", code=promo_code_str, error=str(exc))
                errors_out.append(
                    {"code": promo_code_str, "provider": "stripe_promo", "error": str(exc)}
                )

    await db.flush()
    logger.info(
        "coupon_sync_done",
        fetched=len(fetched),
        imported=len(imported),
        errors=len(errors_out),
        auto_deactivated=len(auto_deactivated),
    )
    return SyncAllResponse(
        fetched=fetched,
        imported=imported,
        errors=errors_out,
        auto_deactivated=auto_deactivated,
    )


def _apply_stripe_data(coupon: CheckoutCoupon, remote: dict, now: datetime) -> None:
    """Update discount/validity fields from Stripe. Preserve local name/description."""
    if remote.get("percent_off") is not None:
        coupon.discount_type = "percentage"
        coupon.discount_value = Decimal(str(remote["percent_off"]))
        coupon.currency = "INR"
    elif remote.get("amount_off") is not None:
        coupon.discount_type = "flat"
        coupon.discount_value = Decimal(str(remote["amount_off"])) / 100
        coupon.currency = (remote.get("currency") or "inr").upper()

    if remote.get("max_redemptions") is not None:
        coupon.max_uses = remote["max_redemptions"]

    stripe_redeemed = remote.get("times_redeemed", 0)
    if stripe_redeemed > (coupon.used_count or 0):
        coupon.used_count = stripe_redeemed

    if remote.get("deleted"):
        coupon.is_active = False

    duration = remote.get("duration")
    if duration:
        coupon.reuse_policy = "single_use" if duration == "once" else "reusable"

    coupon.stripe_synced_at = now
    # Ensure coupon-level rows always have stripe_coupon_id set (backfill for existing rows)
    if coupon.stripe_coupon_id is None:
        coupon.stripe_coupon_id = coupon.code


def _coupon_from_stripe(code: str, remote: dict, now: datetime) -> CheckoutCoupon:
    """Create a new CheckoutCoupon from a Stripe coupon dict."""
    if remote.get("percent_off") is not None:
        discount_type = "percentage"
        discount_value = Decimal(str(remote["percent_off"]))
        currency = "INR"
    else:
        discount_type = "flat"
        discount_value = Decimal(str(remote.get("amount_off", 0))) / 100
        currency = (remote.get("currency") or "inr").upper()

    duration = remote.get("duration")
    reuse_policy = "single_use" if duration == "once" else "reusable"

    return CheckoutCoupon(
        code=code,
        name=remote.get("name") or code,
        discount_type=discount_type,
        discount_value=discount_value,
        currency=currency,
        reuse_policy=reuse_policy,
        max_uses=remote.get("max_redemptions"),
        used_count=remote.get("times_redeemed", 0),
        is_active=not remote.get("deleted", False),
        stripe_synced_at=now,
        stripe_coupon_id=code,  # coupon-level rows: stripe_coupon_id == code
    )


def _apply_stripe_promo_data(
    coupon: CheckoutCoupon, promo: dict, coupon_data: dict, now: datetime
) -> None:
    """Update a promo-code row from Stripe promotion code + embedded coupon data."""
    if coupon_data.get("percent_off") is not None:
        coupon.discount_type = "percentage"
        coupon.discount_value = Decimal(str(coupon_data["percent_off"]))
        coupon.currency = "INR"
    elif coupon_data.get("amount_off") is not None:
        coupon.discount_type = "flat"
        coupon.discount_value = Decimal(str(coupon_data["amount_off"])) / 100
        coupon.currency = (coupon_data.get("currency") or "inr").upper()
    duration = coupon_data.get("duration")
    if duration:
        coupon.reuse_policy = "single_use" if duration == "once" else "reusable"
    coupon.is_active = bool(promo.get("active", True))
    if promo.get("max_redemptions") is not None:
        coupon.max_uses = promo["max_redemptions"]
    stripe_redeemed = promo.get("times_redeemed", 0)
    if stripe_redeemed > (coupon.used_count or 0):
        coupon.used_count = stripe_redeemed
    expires_at = promo.get("expires_at")
    if expires_at is not None:
        coupon.valid_till = datetime.fromtimestamp(expires_at, tz=UTC)
    coupon.stripe_coupon_id = coupon_data.get("id") or coupon.stripe_coupon_id
    coupon.stripe_synced_at = now


def _promo_code_from_stripe(promo: dict, now: datetime) -> CheckoutCoupon:
    """Create a new CheckoutCoupon row from a Stripe promotion code dict."""
    coupon_data: dict = promo.get("coupon", {})
    stripe_coupon_id = coupon_data.get("id", "")
    if coupon_data.get("percent_off") is not None:
        discount_type = "percentage"
        discount_value = Decimal(str(coupon_data["percent_off"]))
        currency = "INR"
    else:
        discount_type = "flat"
        discount_value = Decimal(str(coupon_data.get("amount_off", 0))) / 100
        currency = (coupon_data.get("currency") or "inr").upper()
    duration = coupon_data.get("duration")
    reuse_policy = "single_use" if duration == "once" else "reusable"
    expires_at = promo.get("expires_at")
    return CheckoutCoupon(
        code=promo["code"],
        name=coupon_data.get("name") or promo["code"],
        discount_type=discount_type,
        discount_value=discount_value,
        currency=currency,
        reuse_policy=reuse_policy,
        max_uses=promo.get("max_redemptions"),
        used_count=promo.get("times_redeemed", 0),
        is_active=bool(promo.get("active", True)),
        valid_till=datetime.fromtimestamp(expires_at, tz=UTC) if expires_at is not None else None,
        stripe_coupon_id=stripe_coupon_id,
        stripe_synced_at=now,
    )


@admin_router.get("/sync-issues", response_model=list[SyncIssueOut])
async def list_sync_issues(
    status: str | None = None,
    coupon_code: str | None = None,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    stmt = select(CouponSyncIssue)
    if status:
        stmt = stmt.where(CouponSyncIssue.status == status)
    if coupon_code:
        normalized = coupon_code.strip().upper()
        stmt = stmt.where(func.upper(CouponSyncIssue.coupon_code) == normalized)
    stmt = stmt.order_by(CouponSyncIssue.created_at.desc())
    result = await db.execute(stmt)
    return [_issue_to_out(i) for i in result.scalars().all()]


@admin_router.patch("/sync-issues/{issue_id}", response_model=SyncIssueOut)
async def resolve_sync_issue(
    issue_id: UUID,
    body: SyncIssueUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    issue = await db.scalar(select(CouponSyncIssue).where(CouponSyncIssue.id == issue_id))
    if issue is None:
        raise HTTPException(status_code=404, detail="Sync issue not found")
    issue.status = body.status
    issue.resolved_at = datetime.now(UTC)
    issue.resolved_by = body.resolved_by
    return _issue_to_out(issue)


# ── Cron router (Cloud Scheduler, guarded by WEBHOOK_API_KEY) ─────────────────
# Cloud Scheduler should call POST /v1/internal/coupons/sync every 30 minutes.
# Configure the job with: Authorization: Bearer <WEBHOOK_API_KEY>

cron_router = APIRouter(prefix="/v1/internal/coupons", tags=["coupons-cron"])


@cron_router.post("/sync", response_model=SyncAllResponse)
async def cron_sync_coupons(
    _: None = Depends(verify_webhook_key),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    """Cloud Scheduler endpoint — runs global coupon sync every 30 minutes."""
    return await sync_all_coupons(db=db)
