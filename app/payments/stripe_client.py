"""
Stripe Coupons API — read-only client.

Used exclusively for pulling coupon data into our local cache.
We do not create, update, or delete coupons in Stripe from this service;
all coupon management happens in the Stripe dashboard.

Stripe coupon → our field mapping:
  id               → code  (Stripe uses our code as the coupon ID)
  name             → name
  percent_off      → discount_value  (when discount_type == "percentage")
  amount_off / 100 → discount_value  (when discount_type == "flat"; Stripe stores paise for INR)
  currency         → currency        (for flat coupons)
  max_redemptions  → max_uses
  redeem_by        → valid_till      (Unix timestamp)
  times_redeemed   → used_count reference for cross-PG tracking
  deleted          → is_active inverse
  duration         → reuse_policy    ("once" → "single_use"; "repeating"/"forever" → "reusable")
"""

from __future__ import annotations

import math
from datetime import UTC
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx
import structlog

from app.config import settings

if TYPE_CHECKING:
    from app.db.models import CheckoutCoupon

logger = structlog.get_logger()

_API_URL = "https://api.stripe.com"
_COUPON_ENDPOINT = "/v1/coupons"
_PROMO_CODE_ENDPOINT = "/v1/promotion_codes"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.stripe_api_url or _API_URL,
        auth=(settings.stripe_api_key, ""),
        timeout=15.0,
    )


async def get_coupon(code: str) -> dict | None:
    """Fetch a single coupon by ID. Returns None on 404."""
    log = logger.bind(code=code, fn="get_coupon")
    log.debug("stripe_get_coupon_start")
    async with _client() as client:
        resp = await client.get(f"{_COUPON_ENDPOINT}/{code}")
        if resp.status_code == 404:
            log.debug("stripe_get_coupon_not_found")
            return None
        if not resp.is_success:
            log.error(
                "stripe_get_coupon_error",
                status_code=resp.status_code,
                response_body=resp.text[:500],
                url=str(resp.url),
            )
            resp.raise_for_status()
        data = resp.json()
        log.debug("stripe_get_coupon_ok", data=data)
        return data


async def list_all_coupons() -> list[dict]:
    """Paginate through all Stripe coupons and return them."""
    log = logger.bind(fn="list_all_coupons", base_url=settings.stripe_api_url or _API_URL)
    log.info("stripe_list_coupons_start")

    results: list[dict] = []
    params: dict = {"limit": 100}
    page_num = 0
    async with _client() as client:
        while True:
            page_num += 1
            log.debug(
                "stripe_list_coupons_page",
                page=page_num,
                starting_after=params.get("starting_after"),
            )
            resp = await client.get(_COUPON_ENDPOINT, params=params)
            if not resp.is_success:
                log.error(
                    "stripe_list_coupons_error",
                    status_code=resp.status_code,
                    response_body=resp.text[:500],
                    url=str(resp.url),
                    page=page_num,
                )
                resp.raise_for_status()
            page = resp.json()
            batch = page.get("data", [])
            results.extend(batch)
            log.debug("stripe_list_coupons_page_done", page=page_num, count=len(batch))
            if not page.get("has_more"):
                break
            params["starting_after"] = page["data"][-1]["id"]

    log.info("stripe_list_coupons_done", total=len(results))
    return results


async def list_all_promo_codes() -> list[dict]:
    """Paginate through all active Stripe promotion codes and return them."""
    log = logger.bind(fn="list_all_promo_codes")
    log.info("stripe_list_promo_codes_start")

    results: list[dict] = []
    params: dict = {"limit": 100}
    page_num = 0
    async with _client() as client:
        while True:
            page_num += 1
            log.debug("stripe_list_promo_codes_page", page=page_num)
            resp = await client.get(_PROMO_CODE_ENDPOINT, params=params)
            if not resp.is_success:
                log.error(
                    "stripe_list_promo_codes_error",
                    status_code=resp.status_code,
                    response_body=resp.text[:500],
                )
                resp.raise_for_status()
            page = resp.json()
            batch = page.get("data", [])
            results.extend(batch)
            if not page.get("has_more"):
                break
            params["starting_after"] = page["data"][-1]["id"]

    log.info("stripe_list_promo_codes_done", total=len(results))
    return results


def compare_coupon(local: CheckoutCoupon, remote: dict) -> list[dict]:
    """
    Compare a local DB record against a Stripe coupon dict.
    Returns a list of mismatch dicts: [{"field", "local", "provider"}].
    Used by the single-coupon sync-check endpoint (read-only, informational).
    """
    mismatches: list[dict] = []

    def mismatch(field: str, local_val: object, remote_val: object) -> None:
        mismatches.append({"field": field, "local": str(local_val), "provider": str(remote_val)})

    if local.discount_type == "percentage":
        remote_pct = remote.get("percent_off")
        if remote_pct is not None and abs(float(local.discount_value) - float(remote_pct)) > 0.001:
            mismatch("discount_value", local.discount_value, remote_pct)
        if remote.get("amount_off") is not None:
            mismatch("discount_type", "percentage", "flat")
    else:
        remote_amount = remote.get("amount_off")
        expected_paise = int(Decimal(str(local.discount_value)) * 100)
        if remote_amount is not None and remote_amount != expected_paise:
            mismatch("discount_value", local.discount_value, f"{remote_amount / 100:.2f}")
        if remote.get("percent_off") is not None:
            mismatch("discount_type", "flat", "percentage")
        remote_currency = remote.get("currency", "").upper()
        if remote_currency and remote_currency != local.currency.upper():
            mismatch("currency", local.currency, remote_currency)

    remote_max = remote.get("max_redemptions")
    if local.max_uses != remote_max:
        mismatch("max_uses", local.max_uses, remote_max)

    remote_redeem_by = remote.get("redeem_by")
    if local.valid_till is not None and remote_redeem_by is not None:
        local_ts = math.floor(local.valid_till.astimezone(UTC).timestamp())
        if abs(local_ts - remote_redeem_by) > 60:  # 1-minute tolerance
            mismatch("valid_till", local.valid_till.isoformat(), remote_redeem_by)
    elif (local.valid_till is None) != (remote_redeem_by is None):
        mismatch("valid_till", local.valid_till, remote_redeem_by)

    remote_duration = remote.get("duration")
    if remote_duration:
        expected_reuse = "single_use" if remote_duration == "once" else "reusable"
        if local.reuse_policy != expected_reuse:
            mismatch("reuse_policy", local.reuse_policy, expected_reuse)

    return mismatches
