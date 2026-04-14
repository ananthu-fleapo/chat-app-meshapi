"""
Tests for app/routers/payments.py

Covers:
  POST /v1/payments  — webhook ingestion + balance crediting + coupon logging
  GET  /v1/payments  — payment history for authenticated user
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import make_execute_result, make_jwt


# ── App + dependency overrides ────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=make_execute_result(rows=[]))
    session.scalar = AsyncMock(return_value=None)
    return session


@pytest.fixture
def client(mock_db_session):
    """TestClient with DB session and Redis overridden."""
    from app.main import create_app
    from app.db.session import get_db_session
    from app.cache.redis_client import get_redis

    app = create_app()

    async def _override_db():
        yield mock_db_session

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_redis] = lambda: None

    return TestClient(app, raise_server_exceptions=True)


WEBHOOK_HEADERS = {"Authorization": "Bearer test-webhook-secret"}
JWT_HEADERS = {"Authorization": f"Bearer {make_jwt()}"}


# ── POST /v1/payments ─────────────────────────────────────────────────────────

class TestCreatePayment:

    def test_valid_payment_returns_received(self, client, mock_db_session):
        """Webhook with valid secret ingests event and returns received=true."""
        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock):
            resp = client.post(
                "/v1/payments",
                json={
                    "userId": "user-abc",
                    "paymentId": "pay_001",
                    "provider": "stripe",
                    "currency": "USD",
                    "amount": 1000,
                },
                headers=WEBHOOK_HEADERS,
            )

        assert resp.status_code == 201
        assert resp.json() == {"received": True, "coupon": None}

    def test_payment_credits_user_balance(self, client, mock_db_session):
        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            client.post(
                "/v1/payments",
                json={
                    "userId": "user-abc",
                    "paymentId": "pay_002",
                    "provider": "stripe",
                    "currency": "USD",
                    "amount": 500,
                },
                headers=WEBHOOK_HEADERS,
            )

        mock_credit.assert_called_once()
        assert mock_credit.call_args[0][0] == "user-abc"
        assert mock_credit.call_args[0][1] == Decimal("5.00")

    def test_payment_with_matching_coupon_updates_usage(self, client, mock_db_session):
        from app.db.models import CheckoutCoupon

        coupon = CheckoutCoupon(
            code="SAVE20",
            name="Save 20",
            description="Test coupon",
            discount_type="percentage",
            discount_value=Decimal("20.00"),
            reuse_policy="single_use",
            max_uses=10,
            used_count=0,
            is_active=True,
        )

        mock_db_session.execute.side_effect = [
            make_execute_result(rows=[], scalar=None),  # duplicate payment lookup
            make_execute_result(rows=[coupon], scalar=coupon),  # coupon lookup
            make_execute_result(rows=[], scalar=None),  # prior usage lookup
        ]

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            resp = client.post(
                "/v1/payments",
                json={
                    "userId": "user-abc",
                    "paymentId": "pay_coupon_001",
                    "provider": "stripe",
                    "couponCode": "SAVE20",
                    "couponDiscountAmount": 200,
                    "currency": "USD",
                    "amount": 1000,
                },
                headers=WEBHOOK_HEADERS,
            )

        assert resp.status_code == 201
        assert resp.json()["coupon"]["code"] == "SAVE20"
        assert resp.json()["coupon"]["name"] == "Save 20"
        assert coupon.used_count == 1
        mock_credit.assert_awaited_once()
        assert mock_credit.await_args.args[1] == Decimal("12.00")

    def test_payment_with_locally_unusable_coupon_logs_only_and_invalidates_cache(self, client, mock_db_session):
        from app.db.models import CheckoutCoupon

        coupon = CheckoutCoupon(
            code="COUPON123",
            name="Coupon 123",
            description="Test coupon",
            discount_type="percentage",
            discount_value=Decimal("10.00"),
            reuse_policy="single_use",
            max_uses=10,
            used_count=1,
            is_active=True,
        )
        prior_usage = object()

        mock_db_session.execute.side_effect = [
            make_execute_result(rows=[], scalar=None),  # duplicate payment lookup
            make_execute_result(rows=[coupon], scalar=coupon),  # coupon lookup
            make_execute_result(rows=[prior_usage], scalar=prior_usage),  # prior usage lookup
        ]

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            resp = client.post(
                "/v1/payments",
                json={
                    "userId": "user-abc",
                    "paymentId": "pay_coupon_rejected",
                    "provider": "cashfree",
                    "couponCode": "coupon123",
                    "couponDiscountAmount": 59,
                    "currency": "USD",
                    "amount": 1000,
                },
                headers=WEBHOOK_HEADERS,
            )

        assert resp.status_code == 201
        assert resp.json() == {"received": True, "coupon": None}
        assert coupon.used_count == 1
        mock_credit.assert_awaited_once()
        assert mock_credit.await_args.args[1] == Decimal("10.59")

    def test_payment_with_unknown_coupon_only_logs_event(self, client, mock_db_session):
        mock_db_session.execute.side_effect = [
            make_execute_result(rows=[], scalar=None),
            make_execute_result(rows=[], scalar=None),
        ]

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock):
            resp = client.post(
                "/v1/payments",
                json={
                    "userId": "user-abc",
                    "paymentId": "pay_coupon_unknown",
                    "provider": "cashfree",
                    "couponCode": "MISSING",
                    "couponDiscountAmount": 100,
                    "currency": "USD",
                    "amount": 1000,
                },
                headers=WEBHOOK_HEADERS,
            )

        assert resp.status_code == 201
        assert resp.json() == {"received": True, "coupon": None}

    def test_cashfree_coupon_credit_restores_discount_before_fx_conversion(self, client, mock_db_session):
        rate = MagicMock()
        rate.total_rate = Decimal("80")
        rate.rate = Decimal("80")

        mock_db_session.execute.side_effect = [
            make_execute_result(rows=[], scalar=None),
            make_execute_result(rows=[rate], scalar=rate),
            make_execute_result(rows=[], scalar=None),
        ]

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            resp = client.post(
                "/v1/payments",
                json={
                    "userId": "user-in",
                    "paymentId": "pay_cashfree_coupon_001",
                    "provider": "cashfree",
                    "currency": "INR",
                    "amount": 944,
                    "gstAmount": 144,
                    "couponCode": "SAVE20",
                    "couponDiscountAmount": 200,
                },
                headers=WEBHOOK_HEADERS,
            )

        assert resp.status_code == 201
        mock_credit.assert_awaited_once()
        assert mock_credit.await_args.args[0] == "user-in"
        assert mock_credit.await_args.args[1] == Decimal("0.125")

    def test_duplicate_payment_is_idempotent(self, client, mock_db_session):
        existing = object()
        mock_db_session.execute.return_value = make_execute_result(rows=[existing], scalar=existing)

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            resp = client.post(
                "/v1/payments",
                json={
                    "userId": "user-abc",
                    "paymentId": "pay_duplicate",
                    "provider": "stripe",
                    "currency": "USD",
                    "amount": 1000,
                },
                headers=WEBHOOK_HEADERS,
            )

        assert resp.status_code == 201
        assert resp.json() == {"received": True, "coupon": None}
        mock_credit.assert_not_called()

    def test_missing_required_fields_returns_422(self, client):
        resp = client.post(
            "/v1/payments",
            json={"provider": "stripe", "amount": 100},
            headers=WEBHOOK_HEADERS,
        )
        assert resp.status_code == 422


class TestListPayments:
    def test_returns_empty_list_when_no_payments(self, client, mock_db_session):
        mock_db_session.execute.return_value = make_execute_result(rows=[])

        resp = client.get("/v1/payments", headers=JWT_HEADERS)

        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_coupon_name_and_discount_display(self, client, mock_db_session):
        event = MagicMock()
        event.id = "evt_1"
        event.user_id = "user-abc"
        event.payment_id = "pay_123"
        event.provider = "cashfree"
        event.order_id = "order_123"
        event.currency = "INR"
        event.amount = 59000
        event.amount_usd = 600
        event.coupon_code = "COUPON123"
        event.payment_metadata = None
        event.discount_amount = 5900
        event.created_at = datetime(2026, 4, 9, tzinfo=timezone.utc)

        mock_db_session.execute.side_effect = [
            make_execute_result(rows=[event]),
            make_execute_result(rows=[("COUPON123", "Summer Offer")]),
        ]

        resp = client.get("/v1/payments", headers=JWT_HEADERS)

        assert resp.status_code == 200
        assert resp.json() == [
            {
                "id": "evt_1",
                "user_id": "user-abc",
                "payment_id": "pay_123",
                "provider": "cashfree",
                "order_id": "order_123",
                "currency": "INR",
                "amount": 59000,
                "amount_usd": 600,
                "credited_amount_raw": 600,
                "credited_amount_display": "6.00",
                "coupon_code": "COUPON123",
                "coupon_name": "Summer Offer",
                "discount_amount_raw": 5900,
                "discount_amount_display": "59.00",
                "created_at": "2026-04-09T00:00:00+00:00",
            }
        ]

    def test_returns_null_coupon_name_when_coupon_no_longer_exists(self, client, mock_db_session):
        event = MagicMock()
        event.id = "evt_2"
        event.user_id = "user-abc"
        event.payment_id = "pay_456"
        event.provider = "stripe"
        event.order_id = None
        event.currency = "USD"
        event.amount = 1000
        event.amount_usd = 1000
        event.coupon_code = "MISSING"
        event.payment_metadata = None
        event.discount_amount = 200
        event.created_at = datetime(2026, 4, 9, tzinfo=timezone.utc)

        mock_db_session.execute.side_effect = [
            make_execute_result(rows=[event]),
            make_execute_result(rows=[]),
        ]

        resp = client.get("/v1/payments", headers=JWT_HEADERS)

        assert resp.status_code == 200
        assert resp.json()[0]["coupon_name"] is None
        assert resp.json()[0]["credited_amount_display"] == "10.00"
        assert resp.json()[0]["discount_amount_display"] == "2.00"

    def test_requires_auth(self, client):
        resp = client.get("/v1/payments")
        assert resp.status_code == 401


class TestCentToDollarConversion:
    @pytest.mark.parametrize("cents,expected_usd", [
        (100, Decimal("1.00")),
        (999, Decimal("9.99")),
        (10000, Decimal("100.00")),
        (1, Decimal("0.01")),
        (50, Decimal("0.50")),
    ])
    def test_usd_cents_convert_to_dollars(self, cents, expected_usd):
        assert Decimal(cents) / 100 == expected_usd
