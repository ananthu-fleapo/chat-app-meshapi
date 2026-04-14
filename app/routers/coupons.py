from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from typing import Any, Literal
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.control_plane import ControlPlaneIdentity, get_admin_user, get_control_plane_user
from app.db.models import CheckoutCoupon, CouponUser, PaymentEvent
from app.db.session import get_db_session
from .coupon_utils import (
    _normalize_coupon_code,
    _normalize_user_ids
)

router = APIRouter(tags=["coupons"])
logger = structlog.get_logger()


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


class CouponSummary(PublicCouponSummary):
    user_ids: list[str]


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


class AdminCouponUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    discount_type: Literal["percentage", "flat"] | None = None
    discount_value: Decimal | None = None
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


def _decimal_str(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _coupon_to_summary(
    coupon: CheckoutCoupon,
    discount_amount: Decimal | None = None,
    public: bool = False,
) -> PublicCouponSummary | CouponSummary:
    data = {
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
    }
    if not public:
        data["user_ids"] = (
            [u.user_id for u in coupon.users]
            if ("users" in coupon.__dict__ and coupon.users is not None)
            else []
        )
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
    if coupon.valid_till and coupon.valid_till < datetime.now(timezone.utc):
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


@router.get("/v1/coupons", response_model=list[PublicCouponSummary])
async def list_coupons(
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
):
    now = datetime.now(timezone.utc)
    user_id = identity.sub

    # 1. Base statement: Active, not expired, not at usage limit
    stmt = (
        select(CheckoutCoupon)
        .where(CheckoutCoupon.is_active == True)
        .where(or_(CheckoutCoupon.valid_till.is_(None), CheckoutCoupon.valid_till >= now))
        .where(or_(CheckoutCoupon.max_uses.is_(None), CheckoutCoupon.used_count < CheckoutCoupon.max_uses))
    )

    # 2. Targeting: (Not targeted OR targeted to ME)
    is_targeted = exists().where(CouponUser.coupon_id == CheckoutCoupon.id)
    is_targeted_to_me = exists().where(
        CouponUser.coupon_id == CheckoutCoupon.id, 
        CouponUser.user_id == user_id
    )
    stmt = stmt.where(or_(~is_targeted, is_targeted_to_me))

    # 3. Single Use Policy: (Not single_use OR not used by ME)
    has_used = exists().where(
        PaymentEvent.user_id == user_id,
        func.lower(PaymentEvent.coupon_code) == func.lower(CheckoutCoupon.code)
    )
    stmt = stmt.where(or_(CheckoutCoupon.reuse_policy != "single_use", ~has_used))

    stmt = stmt.order_by(CheckoutCoupon.discount_value.desc())
    # Note: We don't need selectinload(CheckoutCoupon.users) here as user_ids are excluded

    result = await db.execute(stmt)
    coupons = result.scalars().all()

    return [_coupon_to_summary(c, public=True) for c in coupons]


@router.post("/v1/coupons/validate", response_model=CouponValidateResponse)
async def validate_coupon(
    body: CouponValidateRequest,
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
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


admin_router = APIRouter(
    prefix="/v1/admin/coupons",
    tags=["admin-coupons"],
    dependencies=[Depends(get_admin_user)],
)


@admin_router.post("", response_model=CouponSummary, status_code=201)
async def create_coupon(body: AdminCouponCreateRequest, db: AsyncSession = Depends(get_db_session)):
    existing = await db.execute(
        select(CheckoutCoupon)
        .where(func.lower(CheckoutCoupon.code) == _normalize_coupon_code(body.code).lower())
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
        reuse_policy=body.reuse_policy,
        max_uses=body.max_uses,
        valid_till=body.valid_till,
        is_active=body.is_active
    )
    db.add(coupon)
    await db.flush()
    if body.user_ids is not None:
        await _replace_coupon_users(
            db, coupon.id, _normalize_user_ids(body.user_ids)
        )
    await db.refresh(coupon, attribute_names=["users"])
    return _coupon_to_summary(coupon)


@admin_router.get("", response_model=list[CouponSummary])
async def list_admin_coupons(
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db_session),
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
    coupon_id: UUID, body: AdminCouponUpdateRequest, db: AsyncSession = Depends(get_db_session)
):
    stmt = select(CheckoutCoupon).where(CheckoutCoupon.id == coupon_id).options(selectinload(CheckoutCoupon.users))
    coupon = await db.scalar(stmt)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Coupon not found")
    payload = body.model_dump(exclude_unset=True)
    user_ids = payload.pop("user_ids", None)
    for field, value in payload.items():
        setattr(coupon, field, value)

    if user_ids is not None:
        await _replace_coupon_users(
            db, coupon.id, _normalize_user_ids(user_ids)
        )
    await db.refresh(coupon, attribute_names=["users"])
    return _coupon_to_summary(coupon)


@admin_router.delete("/{coupon_id}")
async def delete_coupon(coupon_id: UUID, db: AsyncSession = Depends(get_db_session)):
    coupon = await db.scalar(select(CheckoutCoupon).where(CheckoutCoupon.id == coupon_id))
    if coupon is None:
        raise HTTPException(status_code=404, detail="Coupon not found")
    coupon.is_active = False
    return {"deleted": True}


@admin_router.post("/{coupon_id}/users")
async def assign_coupon_users(
    coupon_id: UUID, body: AssignCouponUsersRequest, db: AsyncSession = Depends(get_db_session)
):
    coupon = await db.scalar(select(CheckoutCoupon).where(CheckoutCoupon.id == coupon_id))
    if coupon is None:
        raise HTTPException(status_code=404, detail="Coupon not found")
    await _replace_coupon_users(
        db, coupon_id, _normalize_user_ids(body.user_ids)
    )
    return {"assigned": len(body.user_ids or [])}


@admin_router.get("/stats", response_model=CouponStatsOut)
async def coupon_stats(db: AsyncSession = Depends(get_db_session)):
    total = await db.scalar(select(func.count()).select_from(CheckoutCoupon)) or 0
    active = (
        await db.scalar(
            select(func.count()).select_from(CheckoutCoupon).where(CheckoutCoupon.is_active.is_(True))
        )
        or 0
    )
    total_usage = (
        await db.scalar(
            select(func.coalesce(func.sum(CheckoutCoupon.used_count), 0)).select_from(CheckoutCoupon)
        )
        or 0
    )
    result = await db.execute(select(CheckoutCoupon).order_by(CheckoutCoupon.used_count.desc()).limit(5))
    most_used = [{"code": coupon.code, "used_count": coupon.used_count} for coupon in result.scalars().all()]
    return CouponStatsOut(total=total, active=active, total_usage=total_usage, most_used=most_used)
