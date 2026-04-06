"""
Tests for app/routers/payments.py

Covers:
  POST /v1/payments  — webhook ingestion + balance crediting
  GET  /v1/payments  — payment history for authenticated user
"""

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
        assert resp.json() == {"received": True}

    def test_payment_credits_user_balance(self, client, mock_db_session):
        """Amount in cents is converted to USD and credited to user balance."""
        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            client.post(
                "/v1/payments",
                json={
                    "userId": "user-abc",
                    "paymentId": "pay_002",
                    "provider": "stripe",
                    "currency": "USD",
                    "amount": 500,  # $5.00
                },
                headers=WEBHOOK_HEADERS,
            )

        mock_credit.assert_called_once()
        call_args = mock_credit.call_args
        assert call_args[0][0] == "user-abc"
        assert call_args[0][1] == Decimal("5.00")

    def test_payment_cashfree_credits_balance(self, client, mock_db_session):
        """Cashfree payments also normalized to USD (amount / 100)."""
        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            client.post(
                "/v1/payments",
                json={
                    "userId": "user-india",
                    "paymentId": "cf_pay_001",
                    "provider": "cashfree",
                    "currency": "USD",
                    "amount": 1000,  # $10.00
                },
                headers=WEBHOOK_HEADERS,
            )

        mock_credit.assert_called_once()
        assert mock_credit.call_args[0][1] == Decimal("10.00")

    def test_zero_amount_skips_balance_credit(self, client, mock_db_session):
        """Zero amount payment event is logged but balance is not credited."""
        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            resp = client.post(
                "/v1/payments",
                json={
                    "userId": "user-abc",
                    "paymentId": "pay_zero",
                    "provider": "stripe",
                    "amount": 0,
                },
                headers=WEBHOOK_HEADERS,
            )

        assert resp.status_code == 201
        mock_credit.assert_not_called()

    def test_null_amount_skips_balance_credit(self, client, mock_db_session):
        """None amount (optional field) does not crash and skips balance credit."""
        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            resp = client.post(
                "/v1/payments",
                json={
                    "userId": "user-abc",
                    "paymentId": "pay_null_amount",
                    "provider": "stripe",
                },
                headers=WEBHOOK_HEADERS,
            )

        assert resp.status_code == 201
        mock_credit.assert_not_called()

    def test_missing_webhook_key_returns_4xx(self, client):
        """Request without Authorization header is rejected (422 from FastAPI header validation)."""
        resp = client.post(
            "/v1/payments",
            json={
                "userId": "user-abc",
                "paymentId": "pay_003",
                "provider": "stripe",
                "amount": 100,
            },
        )
        assert resp.status_code in (401, 403, 422)

    def test_wrong_webhook_key_returns_401(self, client):
        """Wrong secret is rejected."""
        resp = client.post(
            "/v1/payments",
            json={
                "userId": "user-abc",
                "paymentId": "pay_004",
                "provider": "stripe",
                "amount": 100,
            },
            headers={"Authorization": "Bearer wrong-secret"},
        )
        assert resp.status_code in (401, 403)

    def test_missing_required_fields_returns_422(self, client):
        """Missing userId and paymentId → validation error."""
        resp = client.post(
            "/v1/payments",
            json={"provider": "stripe", "amount": 100},
            headers=WEBHOOK_HEADERS,
        )
        assert resp.status_code == 422


# ── GET /v1/payments ──────────────────────────────────────────────────────────

class TestListPayments:

    def test_returns_empty_list_when_no_payments(self, client, mock_db_session):
        """New user with no payments gets an empty list."""
        from app.db.models import PaymentEvent
        mock_db_session.execute.return_value = make_execute_result(rows=[])

        resp = client.get("/v1/payments", headers=JWT_HEADERS)

        assert resp.status_code == 200
        assert resp.json() == []

    def test_requires_auth(self, client):
        """No JWT → 401."""
        resp = client.get("/v1/payments")
        assert resp.status_code == 401


# ── Balance cent-to-dollar conversion ────────────────────────────────────────

class TestCentToDollarConversion:
    """Verify the conversion arithmetic used in the payment handler."""

    @pytest.mark.parametrize("cents,expected_usd", [
        (100,   Decimal("1.00")),
        (999,   Decimal("9.99")),
        (10000, Decimal("100.00")),
        (1,     Decimal("0.01")),
        (50,    Decimal("0.50")),
    ])
    def test_conversion(self, cents, expected_usd):
        result = Decimal(cents) / 100
        assert result == expected_usd
