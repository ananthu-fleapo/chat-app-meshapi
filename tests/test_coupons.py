"""
Tests for app/routers/coupons.py — fetch-first coupon architecture.

Provider calls (stripe_client) are always mocked so tests
run without network access or real PG credentials.
"""

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import jwt as _jwt
import pytest

from tests.conftest import TEST_JWT_SECRET, make_execute_result, make_jwt

os.environ.setdefault("ROUTERSVC_SERVICE_KEY", "test-service-key")


# ── JWT helpers ───────────────────────────────────────────────────────────────

def make_admin_jwt(sub: str = "00000000-0000-0000-0000-000000000001") -> str:
    now = int(datetime.now(UTC).timestamp())
    return _jwt.encode(
        {
            "sub": sub,
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
            "app_metadata": {"permissions": ["mesh_api:admin"]},
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


JWT_HEADERS = {"Authorization": f"Bearer {make_jwt()}"}
ADMIN_HEADERS = {"Authorization": f"Bearer {make_admin_jwt()}"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    session.refresh = AsyncMock()

    def _add(obj):
        if getattr(obj, "id", None) is None:
            try:
                obj.id = uuid4()
            except Exception:
                pass
        if getattr(obj, "created_at", None) is None:
            try:
                obj.created_at = datetime.now(UTC)
            except Exception:
                pass

    session.add.side_effect = _add
    return session


@pytest.fixture
def client(mock_db_session):
    from app.cache.redis_client import get_redis
    from app.db.session import get_db_session
    from app.main import create_app

    app = create_app()

    async def _override_db():
        yield mock_db_session

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_redis] = lambda: None

    from fastapi.testclient import TestClient
    return TestClient(app, raise_server_exceptions=True)


# ── Coupon builders ───────────────────────────────────────────────────────────

def _make_coupon(
    code: str = "SAVE20",
    stripe_synced: bool = False,
    used_count: int = 0,
    max_uses: int | None = 10,
    is_active: bool = True,
    valid_till: datetime | None = None,
):
    from app.db.models import CheckoutCoupon

    coupon = CheckoutCoupon(
        code=code,
        name="Save 20",
        description="Test coupon",
        discount_type="percentage",
        discount_value=Decimal("20.00"),
        currency="INR",
        reuse_policy="single_use",
        max_uses=max_uses,
        used_count=used_count,
        valid_till=valid_till or datetime.now(UTC) + timedelta(days=1),
        is_active=is_active,
        stripe_synced_at=datetime.now(UTC) if stripe_synced else None,
    )
    coupon.id = uuid4()
    coupon.created_at = datetime.now(UTC)
    coupon.updated_at = datetime.now(UTC)
    return coupon


# ── Public listing ────────────────────────────────────────────────────────────

class TestPublicListing:
    def test_list_coupons_returns_applicable_coupons(self, client, mock_db_session):
        coupon = _make_coupon()
        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        resp = client.get("/v1/coupons", headers=JWT_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["code"] == "SAVE20"
        assert "user_ids" not in body[0]

    def test_list_coupons_provider_stripe_filter(self, client, mock_db_session):
        """?provider=stripe only returns coupons with stripe_synced_at set."""
        stripe_coupon = _make_coupon(code="STRIPE10", stripe_synced=True)
        # SQL filtering is done by the endpoint; mock returns only what SQL would return
        mock_db_session.execute.return_value = make_execute_result(
            rows=[stripe_coupon], scalar=None
        )

        resp = client.get("/v1/coupons?provider=stripe", headers=JWT_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["code"] == "STRIPE10"

    def test_list_coupons_no_provider_returns_all(self, client, mock_db_session):
        """No provider param = current behaviour (all active coupons)."""
        coupons = [_make_coupon("SAVE10"), _make_coupon("SAVE20")]
        mock_db_session.execute.return_value = make_execute_result(rows=coupons, scalar=None)

        resp = client.get("/v1/coupons", headers=JWT_HEADERS)

        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_validate_coupon_returns_discount(self, client, mock_db_session):
        coupon = _make_coupon()

        with patch(
            "app.routers.coupons._get_coupon_for_user",
            new=AsyncMock(return_value=(coupon, Decimal("2.00"))),
        ):
            resp = client.post(
                "/v1/coupons/validate",
                json={"code": "SAVE20", "amount": "10.00", "currency": "INR"},
                headers=JWT_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json() == {
            "valid": True,
            "discount_type": "percentage",
            "discount_value": "20.00",
            "discount_amount": "2.00",
        }

    def test_validate_filters_by_active(self, client, mock_db_session):
        from fastapi import HTTPException

        with patch(
            "app.routers.coupons._get_coupon_for_user",
            side_effect=HTTPException(status_code=422, detail="Coupon is inactive"),
        ):
            resp = client.post(
                "/v1/coupons/validate",
                json={"code": "DEAD", "amount": "10.00", "currency": "INR"},
                headers=JWT_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json()["valid"] is False

    def test_validate_filters_by_expiry(self, client, mock_db_session):
        from fastapi import HTTPException

        with patch(
            "app.routers.coupons._get_coupon_for_user",
            side_effect=HTTPException(status_code=422, detail="Coupon has expired"),
        ):
            resp = client.post(
                "/v1/coupons/validate",
                json={"code": "EXPIRED", "amount": "10.00", "currency": "INR"},
                headers=JWT_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json()["valid"] is False


# ── Admin CRUD (local-only, no PG calls) ──────────────────────────────────────

class TestAdminCouponsCRUD:
    def test_admin_create_coupon_local_only(self, client, mock_db_session):
        """POST /v1/admin/coupons must NOT call any PG client."""
        mock_db_session.execute.return_value = make_execute_result(rows=[], scalar=None)

        with patch("app.payments.stripe_client.get_coupon") as mock_stripe:
            resp = client.post(
                "/v1/admin/coupons",
                json={
                    "code": "NEW50",
                    "name": "New 50",
                    "discount_type": "percentage",
                    "discount_value": "50.00",
                    "currency": "INR",
                    "max_uses": 25,
                    "is_active": True,
                },
                headers=ADMIN_HEADERS,
            )

        assert resp.status_code == 201
        assert resp.json()["code"] == "NEW50"
        mock_stripe.assert_not_called()

    def test_admin_update_coupon_local_only(self, client, mock_db_session):
        """PATCH must NOT call any PG client."""
        coupon = _make_coupon()
        mock_db_session.scalar.return_value = coupon
        mock_db_session.execute.return_value = make_execute_result(rows=[], scalar=None)

        with patch("app.payments.stripe_client.list_all_coupons") as mock_stripe:
            resp = client.patch(
                f"/v1/admin/coupons/{coupon.id}",
                json={"name": "Renamed"},
                headers=ADMIN_HEADERS,
            )

        assert resp.status_code == 200
        assert coupon.name == "Renamed"
        mock_stripe.assert_not_called()

    def test_admin_delete_coupon_local_only(self, client, mock_db_session):
        """DELETE must NOT call any PG client and sets is_active=False."""
        coupon = _make_coupon()
        mock_db_session.scalar.return_value = coupon

        with patch("app.payments.stripe_client.list_all_coupons") as mock_stripe:
            resp = client.delete(
                f"/v1/admin/coupons/{coupon.id}",
                headers=ADMIN_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
        assert coupon.is_active is False
        mock_stripe.assert_not_called()

    def test_admin_create_coupon_duplicate_returns_409(self, client, mock_db_session):
        existing = _make_coupon("DUP")
        mock_db_session.execute.return_value = make_execute_result(rows=[existing], scalar=existing)

        resp = client.post(
            "/v1/admin/coupons",
            json={
                "code": "DUP",
                "name": "Dup",
                "discount_type": "percentage",
                "discount_value": "10.00",
            },
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 409

    def test_admin_list_coupons_includes_provider_fields(self, client, mock_db_session):
        coupon = _make_coupon(stripe_synced=True)
        coupon.users = []
        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        resp = client.get("/v1/admin/coupons", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert body[0]["stripe_synced_at"] is not None

    def test_admin_update_does_not_accept_discount_fields(self, client, mock_db_session):
        """discount_type and discount_value are excluded from AdminCouponUpdateRequest."""
        coupon = _make_coupon()
        mock_db_session.scalar.return_value = coupon
        mock_db_session.execute.return_value = make_execute_result(rows=[], scalar=None)

        resp = client.patch(
            f"/v1/admin/coupons/{coupon.id}",
            json={"discount_value": "99.00"},
            headers=ADMIN_HEADERS,
        )

        # Field is ignored (not in schema), coupon value unchanged
        assert resp.status_code == 200
        assert coupon.discount_value == Decimal("20.00")


# ── Sync-all (pull-only) ──────────────────────────────────────────────────────

class TestSyncAll:
    def _local_coupons_result(self, coupons):
        """Mock for the 'SELECT all local coupons' query inside sync_all."""
        return make_execute_result(rows=coupons, scalar=None)

    def test_sync_all_imports_promo_code_from_stripe(self, client, mock_db_session):
        """Stripe promo code not in DB → imported as new record via promo sync."""
        mock_db_session.execute.return_value = make_execute_result(rows=[], scalar=None)

        stripe_coupon = {
            "id": "cpn_IMPORT10",
            "name": "Import 10",
            "percent_off": 10.0,
            "max_redemptions": None,
            "times_redeemed": 0,
            "deleted": False,
            "duration": "once",
        }
        promo_codes = [
            {
                "id": "promo_abc",
                "code": "IMPORT10",
                "active": True,
                "max_redemptions": 50,
                "times_redeemed": 0,
                "coupon": stripe_coupon,
            }
        ]

        added_coupons: list = []

        def _capture_add(obj):
            added_coupons.append(obj)
            if getattr(obj, "id", None) is None:
                from uuid import uuid4
                try:
                    obj.id = uuid4()
                except Exception:
                    pass

        mock_db_session.add.side_effect = _capture_add

        with (
            patch("app.payments.stripe_client.list_all_coupons", new=AsyncMock(return_value=[stripe_coupon])),
            patch("app.payments.stripe_client.list_all_promo_codes", new=AsyncMock(return_value=promo_codes)),
        ):
            resp = client.post("/v1/admin/coupons/sync-all", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert any(i["code"] == "IMPORT10" and i["from"] == "stripe_promo" for i in body["imported"])
        from app.db.models import CheckoutCoupon
        new_rows = [c for c in added_coupons if isinstance(c, CheckoutCoupon)]
        assert len(new_rows) == 1
        assert new_rows[0].code == "IMPORT10"
        assert new_rows[0].stripe_coupon_id == "cpn_IMPORT10"

    def test_sync_all_updates_discount_from_stripe(self, client, mock_db_session):
        """Existing coupon with outdated discount → updated from Stripe."""
        coupon = _make_coupon(code="SAVE10", stripe_synced=True)
        coupon.discount_value = Decimal("10.00")

        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        stripe_coupons = [
            {
                "id": "SAVE10",
                "name": "Save 10",
                "percent_off": 15.0,  # changed to 15
                "max_redemptions": 10,
                "times_redeemed": 0,
                "deleted": False,
            }
        ]

        with (
            patch("app.payments.stripe_client.list_all_coupons", new=AsyncMock(return_value=stripe_coupons)),
            patch("app.payments.stripe_client.list_all_promo_codes", new=AsyncMock(return_value=[])),
        ):
            resp = client.post("/v1/admin/coupons/sync-all", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        # discount_value updated from PG
        assert coupon.discount_value == Decimal("15")

    def test_sync_all_preserves_local_name(self, client, mock_db_session):
        """Sync must NOT overwrite locally-set name/description."""
        coupon = _make_coupon(code="KEEP", stripe_synced=True)
        coupon.name = "Admin Custom Name"

        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        stripe_coupons = [
            {
                "id": "KEEP",
                "name": "Stripe Name",
                "percent_off": 20.0,
                "max_redemptions": None,
                "times_redeemed": 0,
                "deleted": False,
            }
        ]

        with (
            patch("app.payments.stripe_client.list_all_coupons", new=AsyncMock(return_value=stripe_coupons)),
            patch("app.payments.stripe_client.list_all_promo_codes", new=AsyncMock(return_value=[])),
        ):
            resp = client.post("/v1/admin/coupons/sync-all", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        assert coupon.name == "Admin Custom Name"  # not overwritten

    def test_sync_all_auto_deactivates_at_max_uses(self, client, mock_db_session):
        """used_count from Stripe >= max_uses → is_active=False + sync issue logged."""
        coupon = _make_coupon(code="USED100", stripe_synced=True, used_count=95, max_uses=100)

        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        stripe_coupons = [
            {
                "id": "USED100",
                "name": "Used 100",
                "percent_off": 5.0,
                "max_redemptions": 100,
                "times_redeemed": 100,  # exactly at limit
                "deleted": False,
            }
        ]

        with (
            patch("app.payments.stripe_client.list_all_coupons", new=AsyncMock(return_value=stripe_coupons)),
            patch("app.payments.stripe_client.list_all_promo_codes", new=AsyncMock(return_value=[])),
        ):
            resp = client.post("/v1/admin/coupons/sync-all", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert any(ad["code"] == "USED100" for ad in body["auto_deactivated"])
        assert coupon.is_active is False

        # CouponSyncIssue should be logged
        added_issues = [
            call.args[0]
            for call in mock_db_session.add.call_args_list
            if hasattr(call.args[0], "issue_type")
        ]
        assert any(i.issue_type == "auto_deactivated" for i in added_issues)

    def test_sync_all_sets_reuse_policy_from_duration_existing(self, client, mock_db_session):
        """Sync updates reuse_policy from Stripe duration field."""
        coupon = _make_coupon(code="DUR4", stripe_synced=True)
        coupon.reuse_policy = "reusable"
        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        stripe_coupons = [
            {
                "id": "DUR4",
                "name": "Once-off Coupon",
                "percent_off": 20.0,
                "max_redemptions": None,
                "times_redeemed": 0,
                "deleted": False,
                "duration": "once",
            }
        ]

        with (
            patch("app.payments.stripe_client.list_all_coupons", new=AsyncMock(return_value=stripe_coupons)),
            patch("app.payments.stripe_client.list_all_promo_codes", new=AsyncMock(return_value=[])),
        ):
            resp = client.post("/v1/admin/coupons/sync-all", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        assert coupon.reuse_policy == "single_use"

    def test_sync_all_imports_reuse_policy_from_duration_new(self, client, mock_db_session):
        """New promo code imported from Stripe gets reuse_policy set from coupon duration."""
        mock_db_session.execute.return_value = make_execute_result(rows=[], scalar=None)

        stripe_coupon = {
            "id": "cpn_FOREVER50",
            "name": "Forever 50",
            "percent_off": 50.0,
            "max_redemptions": None,
            "times_redeemed": 0,
            "deleted": False,
            "duration": "forever",
        }
        promo_codes = [
            {
                "id": "promo_xyz",
                "code": "FOREVER50",
                "active": True,
                "max_redemptions": None,
                "times_redeemed": 0,
                "coupon": stripe_coupon,
            }
        ]

        added_coupons: list = []

        def _capture_add(obj):
            added_coupons.append(obj)
            if getattr(obj, "id", None) is None:
                from uuid import uuid4
                try:
                    obj.id = uuid4()
                except Exception:
                    pass

        mock_db_session.add.side_effect = _capture_add

        with (
            patch("app.payments.stripe_client.list_all_coupons", new=AsyncMock(return_value=[stripe_coupon])),
            patch("app.payments.stripe_client.list_all_promo_codes", new=AsyncMock(return_value=promo_codes)),
        ):
            resp = client.post("/v1/admin/coupons/sync-all", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        from app.db.models import CheckoutCoupon
        new_coupons = [c for c in added_coupons if isinstance(c, CheckoutCoupon)]
        assert len(new_coupons) == 1
        assert new_coupons[0].reuse_policy == "reusable"

    def test_sync_all_stripe_error_logged(self, client, mock_db_session):
        """Stripe list failure → error in response, no crash."""
        mock_db_session.execute.return_value = make_execute_result(rows=[], scalar=None)

        with (
            patch("app.payments.stripe_client.list_all_coupons", new=AsyncMock(side_effect=Exception("connection refused"))),
            patch("app.payments.stripe_client.list_all_promo_codes", new=AsyncMock(return_value=[])),
        ):
            resp = client.post("/v1/admin/coupons/sync-all", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert any(e["provider"] == "stripe" for e in body["errors"])


# ── Sync check (single coupon) ────────────────────────────────────────────────

class TestSyncCheck:
    def test_sync_check_in_sync(self, client, mock_db_session):
        coupon = _make_coupon(stripe_synced=True)
        coupon.valid_till = None  # avoid valid_till vs redeem_by mismatch
        coupon.reuse_policy = "single_use"
        mock_db_session.scalar.return_value = coupon

        stripe_remote = {
            "percent_off": 20.0,
            "amount_off": None,
            "max_redemptions": 10,
            "redeem_by": None,
            "currency": "inr",
            "duration": "once",
        }

        with patch(
            "app.payments.stripe_client.get_coupon",
            new=AsyncMock(return_value=stripe_remote),
        ):
            resp = client.post(
                f"/v1/admin/coupons/{coupon.id}/sync",
                headers=ADMIN_HEADERS,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["stripe"]["in_sync"] is True

    def test_sync_check_mismatch(self, client, mock_db_session):
        coupon = _make_coupon(stripe_synced=True)
        mock_db_session.scalar.return_value = coupon

        stripe_remote = {
            "percent_off": 99.0,  # different from local 20.0
            "amount_off": None,
            "max_redemptions": 10,
            "redeem_by": None,
        }

        with patch(
            "app.payments.stripe_client.get_coupon",
            new=AsyncMock(return_value=stripe_remote),
        ):
            resp = client.post(
                f"/v1/admin/coupons/{coupon.id}/sync",
                headers=ADMIN_HEADERS,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["stripe"]["in_sync"] is False
        assert any(m["field"] == "discount_value" for m in body["stripe"]["mismatches"])


# ── Sync issues ───────────────────────────────────────────────────────────────

class TestSyncIssues:
    def test_list_sync_issues(self, client, mock_db_session):
        from app.db.models import CouponSyncIssue

        issue = CouponSyncIssue(
            coupon_id=uuid4(),
            coupon_code="FAIL5",
            provider="stripe",
            issue_type="fetch_failed",
            details={"error": "timeout"},
            status="pending",
        )
        issue.id = uuid4()
        issue.created_at = datetime.now(UTC)
        issue.resolved_at = None
        issue.resolved_by = None

        mock_db_session.execute.return_value = make_execute_result(rows=[issue], scalar=None)

        resp = client.get("/v1/admin/coupons/sync-issues", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["coupon_code"] == "FAIL5"
        assert body[0]["status"] == "pending"

    def test_resolve_sync_issue(self, client, mock_db_session):
        from app.db.models import CouponSyncIssue

        issue = CouponSyncIssue(
            coupon_id=uuid4(),
            coupon_code="FAIL5",
            provider="stripe",
            issue_type="fetch_failed",
            details={},
            status="pending",
        )
        issue.id = uuid4()
        issue.created_at = datetime.now(UTC)
        issue.resolved_at = None
        issue.resolved_by = None

        mock_db_session.scalar.return_value = issue

        resp = client.patch(
            f"/v1/admin/coupons/sync-issues/{issue.id}",
            json={"status": "dismissed", "resolved_by": "admin@example.com"},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 200
        assert issue.status == "dismissed"
        assert issue.resolved_by == "admin@example.com"


# ── Webhook auto-deactivation ─────────────────────────────────────────────────

class TestWebhookAutoDeactivation:
    def _make_payment_webhook_body(self, coupon_code: str = "SAVE20") -> dict:
        return {
            "userId": "user-001",
            "paymentId": "pay-001",
            "provider": "stripe",
            "couponCode": coupon_code,
            "amount": 1000,
            "currency": "USD",
        }

    def test_webhook_increments_used_count(self, client, mock_db_session):
        coupon = _make_coupon(used_count=3, max_uses=10)
        mock_db_session.execute = AsyncMock(
            side_effect=[
                make_execute_result(rows=[], scalar=None),   # PaymentEvent lookup (dedup)
                make_execute_result(rows=[coupon], scalar=None),  # coupon fetch
                make_execute_result(rows=[], scalar=None),   # single_use prior usage
            ]
        )
        mock_db_session.scalar = AsyncMock(return_value=None)

        with patch("app.routers.payments.credit_balance", new=AsyncMock()):
            resp = client.post(
                "/v1/payments",
                json=self._make_payment_webhook_body(),
                headers={"Authorization": "Bearer test-webhook-secret"},
            )

        assert resp.status_code == 201
        assert coupon.used_count == 4

    def test_webhook_auto_deactivates_at_max_uses(self, client, mock_db_session):
        """When used_count reaches max_uses via webhook, is_active goes False — no PG call."""
        coupon = _make_coupon(used_count=9, max_uses=10, stripe_synced=True)
        mock_db_session.execute = AsyncMock(
            side_effect=[
                make_execute_result(rows=[], scalar=None),
                make_execute_result(rows=[coupon], scalar=None),
                make_execute_result(rows=[], scalar=None),
            ]
        )
        mock_db_session.scalar = AsyncMock(return_value=None)

        with patch("app.routers.payments.credit_balance", new=AsyncMock()), \
             patch("app.payments.stripe_client.list_all_coupons") as mock_stripe:
            resp = client.post(
                "/v1/payments",
                json=self._make_payment_webhook_body(),
                headers={"Authorization": "Bearer test-webhook-secret"},
            )

        assert resp.status_code == 201
        assert coupon.used_count == 10
        assert coupon.is_active is False
        mock_stripe.assert_not_called()  # no PG calls made

        # CouponSyncIssue auto_deactivated should be logged
        added = [
            call.args[0]
            for call in mock_db_session.add.call_args_list
            if hasattr(call.args[0], "issue_type")
        ]
        assert any(i.issue_type == "auto_deactivated" for i in added)

    def test_webhook_does_not_deactivate_below_max(self, client, mock_db_session):
        coupon = _make_coupon(used_count=4, max_uses=10, stripe_synced=True)
        mock_db_session.execute = AsyncMock(
            side_effect=[
                make_execute_result(rows=[], scalar=None),
                make_execute_result(rows=[coupon], scalar=None),
                make_execute_result(rows=[], scalar=None),
            ]
        )
        mock_db_session.scalar = AsyncMock(return_value=None)

        with patch("app.routers.payments.credit_balance", new=AsyncMock()):
            resp = client.post(
                "/v1/payments",
                json=self._make_payment_webhook_body(),
                headers={"Authorization": "Bearer test-webhook-secret"},
            )

        assert resp.status_code == 201
        assert coupon.is_active is True


# ── Existing test coverage (retained from original test file) ─────────────────

class TestCouponsOriginal:
    def test_list_coupons_does_not_leak_user_ids(self, client, mock_db_session):
        from app.db.models import CouponUser

        coupon = _make_coupon()
        coupon.users = [CouponUser(coupon_id=coupon.id, user_id="user-123")]
        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        resp = client.get("/v1/coupons", headers=JWT_HEADERS)

        assert resp.status_code == 200
        assert "user_ids" not in resp.json()[0]

    def test_admin_update_coupon_replaces_user_assignments(self, client, mock_db_session):
        from app.db.models import CheckoutCoupon, CouponUser

        coupon_id = uuid4()
        coupon = CheckoutCoupon(
            code="SAVE20",
            name="Save 20",
            discount_type="percentage",
            discount_value=Decimal("20.00"),
            currency="INR",
            reuse_policy="single_use",
            max_uses=10,
            used_count=0,
            is_active=True,
        )
        coupon.id = coupon_id
        existing_assignment = CouponUser(coupon_id=coupon_id, user_id="user-old")

        mock_db_session.scalar.return_value = coupon
        mock_db_session.execute.return_value = make_execute_result(
            rows=[existing_assignment], scalar=None
        )

        resp = client.patch(
            f"/v1/admin/coupons/{coupon_id}",
            json={"name": "Save 25", "user_ids": ["user-new"]},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 200
        assert coupon.name == "Save 25"
        mock_db_session.delete.assert_awaited_once_with(existing_assignment)

    def test_admin_list_coupons_includes_user_ids(self, client, mock_db_session):
        from app.db.models import CouponUser

        coupon = _make_coupon()
        coupon.users = [CouponUser(coupon_id=coupon.id, user_id="admin-target")]
        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        resp = client.get("/v1/admin/coupons", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        assert resp.json()[0]["user_ids"] == ["admin-target"]
