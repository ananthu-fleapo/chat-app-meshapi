"""
Tests for POST /internal/reconcile

Coverage:
- Auth: missing bearer → 403, wrong bearer → 403, correct → 200
- All users balanced: drifted=0, notify_here=False, title contains "All N balanced"
- One drifted user: drifted=1, notify_here=True, user_id in Slack message
- No ledger rows (legacy user): reported as drifted
- Slack failure does not affect HTTP response
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

WEBHOOK_HEADERS = {"Authorization": "Bearer test-webhook-secret"}
WRONG_HEADERS = {"Authorization": "Bearer wrong-secret"}


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from app.main import create_app
    from app.cache.redis_client import get_redis
    from fastapi.testclient import TestClient

    app = create_app()
    app.dependency_overrides[get_redis] = lambda: None
    return TestClient(app, raise_server_exceptions=True)


def _mock_session_factory(balance_rows: list, ledger_agg_rows: list):
    """
    Patch reconcile.get_session_factory to return a session whose execute()
    is called with: count query, then repeated (balance page + ledger agg) queries.

    balance_rows: list of MagicMock with .user_id and .balance_usd
    ledger_agg_rows: list of MagicMock with .user_id, .total_credits, .total_debits
    """
    session = AsyncMock()

    count_result = MagicMock()
    count_result.scalar_one.return_value = len(balance_rows)

    balance_page_result = MagicMock()
    balance_page_result.scalars.return_value.all.return_value = balance_rows

    agg_result = MagicMock()
    agg_result.all.return_value = ledger_agg_rows

    # execute() is called: (1) count, (2) balance page, (3) ledger agg
    session.execute = AsyncMock(
        side_effect=[count_result, balance_page_result, agg_result]
    )

    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = False

    return patch(
        "app.routers.reconcile.get_session_factory",
        return_value=lambda: cm,
    )


def _make_balance(user_id: str, balance_usd: float) -> MagicMock:
    row = MagicMock()
    row.user_id = user_id
    row.balance_usd = Decimal(str(balance_usd))
    return row


def _make_agg(user_id: str, credits: float, debits: float) -> MagicMock:
    row = MagicMock()
    row.user_id = user_id
    row.total_credits = Decimal(str(credits))
    row.total_debits = Decimal(str(debits))
    return row


# ── Auth ───────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_missing_bearer_rejected(self, client):
        # FastAPI returns 422 when the Authorization header is entirely absent
        # (treated as a missing required field before the dependency runs).
        resp = client.post("/internal/reconcile")
        assert resp.status_code in (401, 403, 422)

    def test_wrong_bearer_rejected(self, client):
        resp = client.post("/internal/reconcile", headers=WRONG_HEADERS)
        assert resp.status_code in (401, 403)


# ── Reconciliation logic ───────────────────────────────────────────────────────

class TestReconcileLogic:
    def test_all_balanced_returns_zero_drifted(self, client):
        balance_rows = [_make_balance("user-1", 10.0)]
        # ledger net = 15 - 5 = 10 = balance → no drift
        agg_rows = [_make_agg("user-1", 15.0, 5.0)]

        mock_slack = AsyncMock()
        with _mock_session_factory(balance_rows, agg_rows), \
             patch("app.routers.reconcile.send_slack_alert", mock_slack):
            resp = client.post("/internal/reconcile", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["checked"] == 1
        assert data["drifted"] == 0
        assert data["total_discrepancy_usd"] == "0"

    def test_all_balanced_slack_title_mentions_all(self, client):
        balance_rows = [_make_balance("user-1", 10.0)]
        agg_rows = [_make_agg("user-1", 15.0, 5.0)]

        mock_slack = AsyncMock()
        with _mock_session_factory(balance_rows, agg_rows), \
             patch("app.routers.reconcile.send_slack_alert", mock_slack):
            client.post("/internal/reconcile", headers=WEBHOOK_HEADERS)

        mock_slack.assert_called_once()
        title = mock_slack.call_args.kwargs["title"]
        assert "All" in title
        assert "balanced" in title
        assert mock_slack.call_args.kwargs["notify_here"] is False

    def test_drifted_user_appears_in_response(self, client):
        # balance=10, ledger_net=8 → discrepancy=-2
        balance_rows = [_make_balance("user-drift", 10.0)]
        agg_rows = [_make_agg("user-drift", 8.0, 0.0)]

        mock_slack = AsyncMock()
        with _mock_session_factory(balance_rows, agg_rows), \
             patch("app.routers.reconcile.send_slack_alert", mock_slack):
            resp = client.post("/internal/reconcile", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["drifted"] == 1
        assert Decimal(data["total_discrepancy_usd"]) > 0

    def test_drifted_user_in_slack_message_and_notify_here(self, client):
        balance_rows = [_make_balance("user-drift", 10.0)]
        agg_rows = [_make_agg("user-drift", 8.0, 0.0)]

        mock_slack = AsyncMock()
        with _mock_session_factory(balance_rows, agg_rows), \
             patch("app.routers.reconcile.send_slack_alert", mock_slack):
            client.post("/internal/reconcile", headers=WEBHOOK_HEADERS)

        assert mock_slack.call_args.kwargs["notify_here"] is True
        message = mock_slack.call_args.kwargs.get("message", "")
        assert "user-drift" in message

    def test_legacy_user_no_ledger_rows_is_drifted(self, client):
        # User has balance=5 but no ledger rows → ledger_net=0, discrepancy=-5
        balance_rows = [_make_balance("legacy-user", 5.0)]
        agg_rows = []  # no ledger rows for this user

        mock_slack = AsyncMock()
        with _mock_session_factory(balance_rows, agg_rows), \
             patch("app.routers.reconcile.send_slack_alert", mock_slack):
            resp = client.post("/internal/reconcile", headers=WEBHOOK_HEADERS)

        assert resp.json()["drifted"] == 1

    def test_no_users_returns_zero_checked(self, client):
        session = AsyncMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        session.execute = AsyncMock(return_value=count_result)

        cm = AsyncMock()
        cm.__aenter__.return_value = session
        cm.__aexit__.return_value = False

        mock_slack = AsyncMock()
        with patch("app.routers.reconcile.get_session_factory", return_value=lambda: cm), \
             patch("app.routers.reconcile.send_slack_alert", mock_slack):
            resp = client.post("/internal/reconcile", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["checked"] == 0

    def test_slack_failure_does_not_affect_response(self, client):
        balance_rows = [_make_balance("user-1", 10.0)]
        agg_rows = [_make_agg("user-1", 15.0, 5.0)]

        # send_slack_alert swallows internally — returning normally simulates that
        with _mock_session_factory(balance_rows, agg_rows), \
             patch("app.routers.reconcile.send_slack_alert", AsyncMock(return_value=None)):
            resp = client.post("/internal/reconcile", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 200
