"""
Tests for admin analytics endpoints added to app/routers/admin.py.

Covers:
  GET /admin/users/{user_id}/summary
  GET /admin/users/{user_id}/usage
  GET /admin/users/{user_id}/models
  GET /admin/users/{user_id}/events
  GET /admin/usage/timeseries
  GET /admin/payments/summary
  GET /admin/payments/revenue
  GET /admin/payments/countries
  GET /admin/payments/top-users
"""

import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as _jwt
import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET, make_execute_result


# ── Admin JWT helper ──────────────────────────────────────────────────────────

def make_admin_jwt(sub: str = "admin-user-001") -> str:
    now = int(time.time())
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


ADMIN_HEADERS = {"Authorization": f"Bearer {make_admin_jwt()}"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=make_execute_result(rows=[]))
    return session


@pytest.fixture
def client(mock_db):
    from app.main import create_app
    from app.db.session import get_db_session

    app = create_app()

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db_session] = _override_db

    # get_redis() is called directly inside endpoint functions (not via Depends),
    # so dependency_overrides has no effect. Patch at the module level instead so
    # all analytics endpoints see redis=None and skip caching in tests.
    with patch("app.routers.admin.get_redis", return_value=None):
        yield TestClient(app, raise_server_exceptions=True)


# ── /admin/users/{user_id}/summary ───────────────────────────────────────────

class TestUserSummary:

    def test_user_with_no_keys_returns_zeros(self, client, mock_db):
        """User that has no keys should return all-zero summary without raising."""
        # keys aggregate query returns zero counts
        keys_row = MagicMock(key_count=0, active_key_count=0, created_at=None)
        # key_ids query returns empty
        # balance query returns None
        user_row = MagicMock(email="user@example.com", display_name="Test User")
        mock_db.execute.side_effect = [
            make_execute_result(rows=[keys_row]),   # keys aggregate
            make_execute_result(rows=[]),             # key_ids list
            make_execute_result(scalar=None),         # balance
            make_execute_result(scalar=0),            # total recharged (payment_events sum)
            make_execute_result(rows=[user_row]),     # user details
            make_execute_result(scalar=0.0),          # total paid
        ]

        resp = client.get("/admin/users/unknown-user/summary", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "unknown-user"
        assert data["key_count"] == 0
        assert data["active_key_count"] == 0
        assert data["api_calls"] == 0
        assert data["total_spent_usd"] == "0"
        assert data["balance_usd"] is None

    def test_user_with_keys_and_spend(self, client, mock_db):
        """User with keys returns correct aggregated spend and call count."""
        import uuid

        key_id = uuid.uuid4()
        keys_row = MagicMock(
            key_count=2,
            active_key_count=1,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        spend_row = MagicMock(
            api_calls=42,
            total_spent=Decimal("1.2345"),
            last_activity=datetime(2026, 1, 15, tzinfo=timezone.utc),
        )
        key_id_row = MagicMock()
        key_id_row.__getitem__ = lambda self, i: key_id

        user_row = MagicMock(email="user@example.com", display_name="Test User")
        mock_db.execute.side_effect = [
            make_execute_result(rows=[keys_row]),
            make_execute_result(rows=[(key_id,)]),
            make_execute_result(rows=[spend_row]),
            make_execute_result(scalar=Decimal("5.00")),
            make_execute_result(scalar=1500),         # total recharged (payment_events sum in cents)
            make_execute_result(rows=[user_row]),     # user details
            make_execute_result(scalar=10.0),         # total paid
        ]

        resp = client.get("/admin/users/user-abc/summary", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["key_count"] == 2
        assert data["active_key_count"] == 1
        assert data["api_calls"] == 42
        assert data["balance_usd"] == "5.00"
        # total_recharged = Decimal(1500) / 100 = 15.00; balance = 5.00; total_spent = 15.00 - 5.00
        assert data["total_spent_usd"] == "10.00"


# ── /admin/users/{user_id}/usage ─────────────────────────────────────────────

class TestUserUsageTimeseries:

    def _make_bucket_row(self, bucket_str: str, requests: int, cost: str):
        row = MagicMock()
        row.bucket = datetime.fromisoformat(bucket_str)
        row.requests = requests
        row.cost_usd = Decimal(cost)
        return row

    def test_no_keys_returns_empty(self, client, mock_db):
        mock_db.execute.side_effect = [
            make_execute_result(rows=[]),  # key_ids
        ]
        resp = client.get("/admin/users/nobody/usage?range=7d", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_24h_range_returns_series(self, client, mock_db):
        import uuid

        key_id = uuid.uuid4()
        bucket_row = self._make_bucket_row("2026-04-06T10:00:00+00:00", 5, "0.0012")

        mock_db.execute.side_effect = [
            make_execute_result(rows=[(key_id,)]),
            make_execute_result(rows=[bucket_row]),
        ]

        resp = client.get("/admin/users/user-x/usage?range=24h", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["requests"] == 5
        assert "bucket" in data[0]
        assert "cost_usd" in data[0]

    def test_7d_range_returns_series(self, client, mock_db):
        import uuid

        key_id = uuid.uuid4()
        bucket_row = self._make_bucket_row("2026-04-01T00:00:00+00:00", 100, "2.50")

        mock_db.execute.side_effect = [
            make_execute_result(rows=[(key_id,)]),
            make_execute_result(rows=[bucket_row]),
        ]

        resp = client.get("/admin/users/user-x/usage?range=7d", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["requests"] == 100


# ── /admin/users/{user_id}/models ────────────────────────────────────────────

class TestUserModelBreakdown:

    def test_no_keys_returns_empty(self, client, mock_db):
        mock_db.execute.return_value = make_execute_result(rows=[])
        resp = client.get("/admin/users/nobody/models", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_sorted_by_cost(self, client, mock_db):
        import uuid

        key_id = uuid.uuid4()
        row1 = MagicMock(model="openai/gpt-4o", requests=10, success=9, tokens=5000, cost=Decimal("0.50"))
        row2 = MagicMock(model="openai/gpt-4o-mini", requests=50, success=48, tokens=10000, cost=Decimal("0.10"))

        mock_db.execute.side_effect = [
            make_execute_result(rows=[(key_id,)]),
            make_execute_result(rows=[row1, row2]),
        ]

        resp = client.get("/admin/users/user-x/models", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["model"] == "openai/gpt-4o"
        assert data[0]["requests"] == 10


# ── /admin/users/{user_id}/events ────────────────────────────────────────────

class TestUserEvents:

    def test_no_keys_returns_empty_page(self, client, mock_db):
        mock_db.execute.return_value = make_execute_result(rows=[])
        resp = client.get("/admin/users/nobody/events", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["events"] == []

    def test_pagination_params_respected(self, client, mock_db):
        import uuid

        key_id = uuid.uuid4()
        event = MagicMock()
        event.id = uuid.uuid4()
        event.key_id = key_id
        event.request_id = "req_001"
        event.model = "openai/gpt-4o-mini"
        event.stream = False
        event.prompt_tokens = 10
        event.completion_tokens = 20
        event.total_tokens = 30
        event.cost_usd = Decimal("0.0001")
        event.latency_ms = 500
        event.status = "success"
        event.error_code = None
        event.created_at = datetime(2026, 4, 1, tzinfo=timezone.utc)

        mock_db.execute.side_effect = [
            make_execute_result(rows=[(key_id, {"label": "test-key"})]),  # key_map
            make_execute_result(scalar=1),                                   # count
            make_execute_result(rows=[event]),                               # events scalars
        ]
        # scalars().all() needs special handling
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [event]

        mock_db.execute.side_effect = [
            make_execute_result(rows=[(key_id, {"label": "test-key"})]),
            count_result,
            events_result,
        ]

        resp = client.get("/admin/users/user-x/events?limit=1&offset=0", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 1
        assert data["offset"] == 0

    def test_filter_by_status(self, client, mock_db):
        import uuid

        key_id = uuid.uuid4()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            make_execute_result(rows=[(key_id, None)]),
            count_result,
            events_result,
        ]

        resp = client.get("/admin/users/user-x/events?status=error", headers=ADMIN_HEADERS)
        assert resp.status_code == 200


# ── /admin/usage/timeseries ───────────────────────────────────────────────────

class TestSystemTimeseries:

    def _make_bucket_row(self, bucket_str: str, requests: int, cost: str):
        row = MagicMock()
        row.bucket = datetime.fromisoformat(bucket_str)
        row.requests = requests
        row.cost_usd = Decimal(cost)
        return row

    def test_returns_series(self, client, mock_db):
        row = self._make_bucket_row("2026-04-01T00:00:00+00:00", 200, "5.00")
        mock_db.execute.return_value = make_execute_result(rows=[row])

        resp = client.get("/admin/usage/timeseries?range=7d", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["requests"] == 200

    def test_empty_data_returns_empty_list(self, client, mock_db):
        mock_db.execute.return_value = make_execute_result(rows=[])
        resp = client.get("/admin/usage/timeseries?range=30d", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []


# ── /admin/payments/summary ───────────────────────────────────────────────────

class TestPaymentSummary:

    def test_no_payments_returns_zeros(self, client, mock_db):
        # The mock returns the result of the SQL expression (already in USD).
        mock_db.execute.side_effect = [
            make_execute_result(scalar=0.0),  # total revenue
            make_execute_result(scalar=0.0),  # today revenue
            make_execute_result(scalar=0.0),  # month revenue
            make_execute_result(scalar=0),    # total transactions count
        ]
        resp = client.get("/admin/payments/summary", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert float(data["total_revenue"]) == pytest.approx(0.0)
        assert float(data["today_revenue"]) == pytest.approx(0.0)
        assert float(data["month_revenue"]) == pytest.approx(0.0)

    def test_payment_today_appears_in_all_buckets(self, client, mock_db):
        # The SQL expression returns amounts already converted to USD.
        # A $10.00 payment → mock returns 10.0 (SQL already divided by 100 and rate).
        mock_db.execute.side_effect = [
            make_execute_result(scalar=10.0),  # total revenue
            make_execute_result(scalar=10.0),  # today revenue
            make_execute_result(scalar=10.0),  # month revenue
            make_execute_result(scalar=1),     # total transactions count
        ]
        resp = client.get("/admin/payments/summary", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert float(data["total_revenue"]) == pytest.approx(10.0)
        assert float(data["today_revenue"]) == pytest.approx(10.0)
        assert float(data["month_revenue"]) == pytest.approx(10.0)


# ── /admin/payments/revenue ───────────────────────────────────────────────────

class TestPaymentRevenue:

    def test_groups_by_day(self, client, mock_db):
        # SQL expression computes USD amount directly; mock returns the computed value.
        # Revenue query groups only by date (no currency column) after USD conversion.
        row1 = MagicMock(date=datetime(2026, 4, 1, tzinfo=timezone.utc), amount=5.0)
        row2 = MagicMock(date=datetime(2026, 4, 2, tzinfo=timezone.utc), amount=3.0)
        mock_db.execute.return_value = make_execute_result(rows=[row1, row2])

        resp = client.get("/admin/payments/revenue?range=30d", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert float(data[0]["amount"]) == pytest.approx(5.0)
        assert float(data[1]["amount"]) == pytest.approx(3.0)
        assert data[0]["currency"] == "USD"

    def test_empty_returns_empty_list(self, client, mock_db):
        mock_db.execute.return_value = make_execute_result(rows=[])
        resp = client.get("/admin/payments/revenue?range=7d", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []


# ── /admin/payments/countries ─────────────────────────────────────────────────

class TestPaymentCountries:

    def test_groups_by_country(self, client, mock_db):
        # SQL expression returns USD amounts; mock reflects the post-conversion value.
        row = MagicMock(country="IN", count=5, amount=20.0)
        mock_db.execute.return_value = make_execute_result(rows=[row])

        resp = client.get("/admin/payments/countries", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["country"] == "IN"
        assert data[0]["count"] == 5
        assert float(data[0]["amount"]) == pytest.approx(20.0)

    def test_null_country_bucketed_as_unknown(self, client, mock_db):
        """Rows with no country in metadata should appear as 'Unknown'."""
        row = MagicMock(country="Unknown", count=3, amount=500)
        mock_db.execute.return_value = make_execute_result(rows=[row])

        resp = client.get("/admin/payments/countries", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["country"] == "Unknown"

    def test_empty_returns_empty_list(self, client, mock_db):
        mock_db.execute.return_value = make_execute_result(rows=[])
        resp = client.get("/admin/payments/countries", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []


# ── /admin/payments/top-users ────────────────────────────────────────────────

class TestPaymentTopUsers:

    def test_returns_rows_without_email(self, client, mock_db):
        row = MagicMock(owner="user-123", requests=10, success=10, cost=Decimal("100.00"))
        mock_db.execute.return_value = make_execute_result(rows=[row])

        resp = client.get("/admin/payments/top-users?limit=10", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "owner": "user-123",
                "email": None,
                "requests": 10,
                "successful_requests": 10,
                "total_tokens": None,
                "total_cost_usd": "100.0000",
            }
        ]


# ── Analytics cache ───────────────────────────────────────────────────────────

class TestAnalyticsCache:

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        from app.cache.analytics_cache import get_analytics_cached

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)

        result = await get_analytics_cached(redis, "some:key")
        assert result is None
        redis.get.assert_called_once_with("some:key")

    @pytest.mark.asyncio
    async def test_cache_hit_returns_value(self):
        from app.cache.analytics_cache import get_analytics_cached

        redis = AsyncMock()
        redis.get = AsyncMock(return_value='{"requests": 5}')

        result = await get_analytics_cached(redis, "some:key")
        assert result == '{"requests": 5}'

    @pytest.mark.asyncio
    async def test_set_stores_with_ttl(self):
        from app.cache.analytics_cache import set_analytics_cached

        redis = AsyncMock()
        redis.set = AsyncMock()

        await set_analytics_cached(redis, "my:key", '{"data": 1}', ttl=60)
        redis.set.assert_called_once_with("my:key", '{"data": 1}', ex=60)

    @pytest.mark.asyncio
    async def test_redis_error_does_not_raise(self):
        """Cache errors must be swallowed — never propagate to callers."""
        from app.cache.analytics_cache import get_analytics_cached, set_analytics_cached

        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=Exception("Redis down"))
        redis.set = AsyncMock(side_effect=Exception("Redis down"))

        # Neither should raise
        result = await get_analytics_cached(redis, "key")
        assert result is None
        await set_analytics_cached(redis, "key", "val")
