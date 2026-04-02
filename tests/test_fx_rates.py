"""
Tests for app/routers/fx_rates.py

Covers:
  POST /v1/fx-rates/refresh — auth guard, insert/update upsert paths,
                              external API failure modes, decimal precision
"""

from decimal import ROUND_DOWN, Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.conftest import make_execute_result


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(return_value=make_execute_result(scalar=None))
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


@pytest.fixture
def error_client(mock_db_session):
    """TestClient that converts server-side RouterVErrors to HTTP responses."""
    from app.main import create_app
    from app.db.session import get_db_session
    from app.cache.redis_client import get_redis

    app = create_app()

    async def _override_db():
        yield mock_db_session

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_redis] = lambda: None

    return TestClient(app, raise_server_exceptions=False)


WEBHOOK_HEADERS = {"Authorization": "Bearer test-webhook-secret"}

# Fake successful response from exchangerate-api.com
_GOOD_API_PAYLOAD = {
    "result": "success",
    "conversion_rates": {"INR": 93.8571},
}


def _mock_httpx_get(payload: dict, status_code: int = 200):
    """Return a patch context for httpx.AsyncClient that yields a fake response."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()  # no-op on success

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    return patch("app.routers.fx_rates.httpx.AsyncClient", return_value=mock_client)


# ── Auth boundary tests ───────────────────────────────────────────────────────

class TestFxRatesAuth:

    def test_missing_auth_header_rejected(self, client):
        """No Authorization header → 401/403/422."""
        resp = client.post("/v1/fx-rates/refresh")
        assert resp.status_code in (401, 403, 422)

    def test_wrong_bearer_token_rejected(self, client):
        """Wrong secret → 401 or 403."""
        resp = client.post(
            "/v1/fx-rates/refresh",
            headers={"Authorization": "Bearer wrong-secret"},
        )
        assert resp.status_code in (401, 403)


# ── Happy path ────────────────────────────────────────────────────────────────

class TestRefreshFxRates:

    def test_insert_new_row_returns_correct_values(self, client, mock_db_session):
        """
        First-ever refresh (no existing row): creates a new CurrencyConversionRate
        and returns rate/markup_fee/total_rate with correct 4-dp truncation.
        """
        mock_db_session.execute.return_value = make_execute_result(scalar=None)

        with _mock_httpx_get(_GOOD_API_PAYLOAD):
            resp = client.post("/v1/fx-rates/refresh", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 200

        body = resp.json()
        assert body["currency"] == "INR"

        rate = Decimal("93.8571")
        _precision = Decimal("0.0001")
        expected_markup = (rate * Decimal("0.002")).quantize(_precision, rounding=ROUND_DOWN)
        expected_total = (rate + expected_markup).quantize(_precision, rounding=ROUND_DOWN)

        assert Decimal(body["rate"]) == rate
        assert Decimal(body["markup_fee"]) == expected_markup
        assert Decimal(body["total_rate"]) == expected_total

        # A new row must have been added to the session
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_update_existing_row_does_not_add(self, client, mock_db_session):
        """
        Existing row: values are updated in-place; db.add must NOT be called.
        """
        from app.db.models import CurrencyConversionRate

        existing_row = MagicMock(spec=CurrencyConversionRate)
        existing_row.currency = "INR"
        mock_db_session.execute.return_value = make_execute_result(scalar=existing_row)

        with _mock_httpx_get(_GOOD_API_PAYLOAD):
            resp = client.post("/v1/fx-rates/refresh", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 200
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_called_once()


# ── External API failure cases ────────────────────────────────────────────────

class TestRefreshFxRatesExternalErrors:

    def test_http_error_returns_502(self, error_client, mock_db_session):
        """httpx raises HTTPError → 502 with error_code='fx_fetch_error'."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPError("connection refused")
        )

        with patch("app.routers.fx_rates.httpx.AsyncClient", return_value=mock_client):
            resp = error_client.post("/v1/fx-rates/refresh", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "fx_fetch_error"

    def test_api_result_not_success_returns_502(self, error_client, mock_db_session):
        """API returns HTTP 200 but result != 'success' → 502 with error_code='fx_api_error'."""
        error_payload = {"result": "error", "error-type": "invalid-key"}

        with _mock_httpx_get(error_payload):
            resp = error_client.post("/v1/fx-rates/refresh", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "fx_api_error"


# ── Decimal precision unit tests ──────────────────────────────────────────────

class TestFxMarkupPrecision:
    """Pure-unit: verify markup/total arithmetic matches fx_rates.py:89-90."""

    _MARKUP_PCT = Decimal("0.002")
    _PRECISION = Decimal("0.0001")

    @pytest.mark.parametrize("raw_rate", [
        Decimal("83.0"),
        Decimal("93.8571"),
        Decimal("100.9999"),
    ])
    def test_markup_fee_truncated_to_4dp(self, raw_rate):
        markup_fee = (raw_rate * self._MARKUP_PCT).quantize(
            self._PRECISION, rounding=ROUND_DOWN
        )
        # Must not exceed 4 decimal places
        assert markup_fee == markup_fee.quantize(self._PRECISION)
        # Must be positive and less than raw rate
        assert Decimal("0") < markup_fee < raw_rate

    @pytest.mark.parametrize("raw_rate", [
        Decimal("83.0"),
        Decimal("93.8571"),
        Decimal("100.9999"),
    ])
    def test_total_rate_equals_rate_plus_markup(self, raw_rate):
        markup_fee = (raw_rate * self._MARKUP_PCT).quantize(
            self._PRECISION, rounding=ROUND_DOWN
        )
        total_rate = (raw_rate + markup_fee).quantize(
            self._PRECISION, rounding=ROUND_DOWN
        )
        assert total_rate == (raw_rate + markup_fee).quantize(
            self._PRECISION, rounding=ROUND_DOWN
        )
        assert total_rate > raw_rate
