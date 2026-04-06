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


# ── INR payment conversion ────────────────────────────────────────────────────

class TestInrPaymentConversion:
    """INR payment conversion and GST deduction logic (POST /v1/payments)."""

    def _make_rate(self, rate="83.0", total_rate="83.5"):
        rate_mock = MagicMock()
        rate_mock.rate = Decimal(rate)
        rate_mock.total_rate = Decimal(total_rate) if total_rate is not None else None
        return rate_mock

    def test_inr_without_gst_converts_full_amount(self, client, mock_db_session):
        """INR payment with no gstAmount: full paise ÷ 100 divided by total_rate."""
        mock_db_session.execute.return_value = make_execute_result(scalar=self._make_rate(total_rate="83.5"))

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            resp = client.post(
                "/v1/payments",
                json={
                    "userId": "user-india",
                    "paymentId": "cf_inr_001",
                    "provider": "cashfree",
                    "currency": "INR",
                    "amount": 8350,  # ₹83.50 in paise
                    "country": "IN",
                },
                headers=WEBHOOK_HEADERS,
            )

        assert resp.status_code == 201
        mock_credit.assert_called_once()
        amount_usd = mock_credit.call_args[0][1]
        assert amount_usd == Decimal("83.50") / Decimal("83.5")

    def test_inr_with_gst_deducts_before_conversion(self, client, mock_db_session):
        """gstAmount > 0: GST component removed from paise amount before USD conversion."""
        mock_db_session.execute.return_value = make_execute_result(scalar=self._make_rate(total_rate="83.5"))

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            resp = client.post(
                "/v1/payments",
                json={
                    "userId": "user-india",
                    "paymentId": "cf_inr_002",
                    "provider": "cashfree",
                    "currency": "INR",
                    "amount": 11800,   # ₹118 total in paise (₹100 base + ₹18 GST)
                    "country": "IN",
                    "gstAmount": 1800, # ₹18 GST in paise (same unit as amount)
                },
                headers=WEBHOOK_HEADERS,
            )

        assert resp.status_code == 201
        mock_credit.assert_called_once()
        # (11800 - 1800) / 100 / 83.5 = ₹100 base / 83.5
        assert mock_credit.call_args[0][1] == Decimal("100.00") / Decimal("83.5")

    def test_inr_with_gst_zero_uses_full_amount(self, client, mock_db_session):
        """gstAmount=0: no deduction — full amount used for conversion."""
        mock_db_session.execute.return_value = make_execute_result(scalar=self._make_rate(total_rate="83.5"))

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            client.post(
                "/v1/payments",
                json={
                    "userId": "user-india",
                    "paymentId": "cf_inr_003",
                    "provider": "cashfree",
                    "currency": "INR",
                    "amount": 8350,
                    "country": "IN",
                    "gstAmount": 0,
                },
                headers=WEBHOOK_HEADERS,
            )

        assert mock_credit.call_args[0][1] == Decimal("83.50") / Decimal("83.5")

    def test_inr_with_null_gst_uses_full_amount(self, client, mock_db_session):
        """gstAmount=None: no deduction — full amount used for conversion."""
        mock_db_session.execute.return_value = make_execute_result(scalar=self._make_rate(total_rate="83.5"))

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            client.post(
                "/v1/payments",
                json={
                    "userId": "user-india",
                    "paymentId": "cf_inr_004",
                    "provider": "cashfree",
                    "currency": "INR",
                    "amount": 8350,
                    "country": "IN",
                    "gstAmount": None,
                },
                headers=WEBHOOK_HEADERS,
            )

        assert mock_credit.call_args[0][1] == Decimal("83.50") / Decimal("83.5")

    def test_falls_back_to_rate_when_total_rate_is_null(self, client, mock_db_session):
        """When total_rate is None, the base rate is used for conversion."""
        mock_db_session.execute.return_value = make_execute_result(scalar=self._make_rate(rate="83.0", total_rate=None))

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock) as mock_credit:
            client.post(
                "/v1/payments",
                json={
                    "userId": "user-india",
                    "paymentId": "cf_inr_005",
                    "provider": "cashfree",
                    "currency": "INR",
                    "amount": 8300,
                    "country": "IN",
                },
                headers=WEBHOOK_HEADERS,
            )

        assert mock_credit.call_args[0][1] == Decimal("83.00") / Decimal("83.0")

    def test_missing_conversion_rate_returns_422(self, client, mock_db_session):
        """No conversion rate row for currency → 422 Unprocessable Entity."""
        mock_db_session.execute.return_value = make_execute_result(scalar=None)

        resp = client.post(
            "/v1/payments",
            json={
                "userId": "user-india",
                "paymentId": "cf_inr_no_rate",
                "provider": "cashfree",
                "currency": "INR",
                "amount": 8350,
            },
            headers=WEBHOOK_HEADERS,
        )

        assert resp.status_code == 422


# ── GstinRecord creation ──────────────────────────────────────────────────────

class TestGstinRecord:
    """GstinRecord rows created (or not) based on country and gstAmount."""

    def _make_rate(self):
        rate_mock = MagicMock()
        rate_mock.rate = Decimal("83.0")
        rate_mock.total_rate = Decimal("83.5")
        return rate_mock

    def _added_gstin_records(self, mock_db_session):
        from app.db.models import GstinRecord
        return [
            call.args[0]
            for call in mock_db_session.add.call_args_list
            if isinstance(call.args[0], GstinRecord)
        ]

    def test_indian_payment_creates_gstin_record(self, client, mock_db_session):
        """country='IN' + gstAmount set → one GstinRecord is created."""
        mock_db_session.execute.return_value = make_execute_result(scalar=self._make_rate())

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock):
            client.post(
                "/v1/payments",
                json={
                    "userId": "user-india",
                    "paymentId": "cf_gstin_001",
                    "provider": "cashfree",
                    "currency": "INR",
                    "amount": 11800,
                    "country": "IN",
                    "gstin": "29ABCDE1234F1Z5",
                    "gstAmount": 18.0,
                },
                headers=WEBHOOK_HEADERS,
            )

        records = self._added_gstin_records(mock_db_session)
        assert len(records) == 1
        assert records[0].gstin == "29ABCDE1234F1Z5"
        assert records[0].gst_amount == Decimal("18.0")

    def test_gstin_record_gstin_is_none_when_not_provided(self, client, mock_db_session):
        """No GSTIN in request → GstinRecord.gstin is None (18% GST charged case)."""
        mock_db_session.execute.return_value = make_execute_result(scalar=self._make_rate())

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock):
            client.post(
                "/v1/payments",
                json={
                    "userId": "user-india",
                    "paymentId": "cf_gstin_002",
                    "provider": "cashfree",
                    "currency": "INR",
                    "amount": 11800,
                    "country": "IN",
                    "gstAmount": 18.0,
                },
                headers=WEBHOOK_HEADERS,
            )

        records = self._added_gstin_records(mock_db_session)
        assert len(records) == 1
        assert records[0].gstin is None

    def test_non_indian_payment_does_not_create_gstin_record(self, client, mock_db_session):
        """Non-IN country → no GstinRecord created."""
        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock):
            client.post(
                "/v1/payments",
                json={
                    "userId": "user-us",
                    "paymentId": "stripe_gstin_001",
                    "provider": "stripe",
                    "currency": "USD",
                    "amount": 1000,
                    "country": "US",
                },
                headers=WEBHOOK_HEADERS,
            )

        assert self._added_gstin_records(mock_db_session) == []

    def test_indian_payment_without_gst_amount_skips_gstin_record(self, client, mock_db_session):
        """country='IN' but gstAmount is None → condition not met, no GstinRecord."""
        mock_db_session.execute.return_value = make_execute_result(scalar=self._make_rate())

        with patch("app.routers.payments.credit_balance", new_callable=AsyncMock):
            client.post(
                "/v1/payments",
                json={
                    "userId": "user-india",
                    "paymentId": "cf_gstin_003",
                    "provider": "cashfree",
                    "currency": "INR",
                    "amount": 8350,
                    "country": "IN",
                },
                headers=WEBHOOK_HEADERS,
            )

        assert self._added_gstin_records(mock_db_session) == []
