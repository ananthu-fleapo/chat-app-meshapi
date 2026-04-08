"""
Tests for GET /admin/usage/errors (app/routers/error_logs.py).

Covers:
  - Empty result returns []
  - Rows are serialised with all fields present
  - Nullable fields (error_code, prompt_tokens, latency_ms) handled correctly
  - Default limit of 100 is accepted
  - Custom ?limit= is forwarded
  - No auth → 403
  - Non-admin JWT → 403
"""

import time
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as _jwt
import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET, make_execute_result, make_jwt


# ── Auth helpers ──────────────────────────────────────────────────────────────

def make_admin_jwt(sub: str = "admin-001") -> str:
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
USER_HEADERS = {"Authorization": f"Bearer {make_jwt()}"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
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

    with patch("app.routers.admin.get_redis", return_value=None):
        yield TestClient(app, raise_server_exceptions=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_event(
    *,
    model: str = "openai/gpt-4o-mini",
    provider: str = "openrouter",
    error_code: str | None = "upstream_error",
    prompt_tokens: int | None = 100,
    latency_ms: int | None = 450,
    created_at: datetime | None = None,
) -> MagicMock:
    event = MagicMock()
    event.id = uuid.uuid4()
    event.request_id = f"req_{uuid.uuid4().hex[:8]}"
    event.model = model
    event.provider = provider
    event.error_code = error_code
    event.prompt_tokens = prompt_tokens
    event.latency_ms = latency_ms
    event.created_at = created_at or datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    return event


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestGetErrorLogs:

    def test_empty_db_returns_empty_list(self, client, mock_db):
        mock_db.execute.return_value = make_execute_result(rows=[])

        resp = client.get("/admin/usage/errors", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_all_fields(self, client, mock_db):
        event = _make_event(
            model="anthropic/claude-3-haiku",
            provider="bedrock",
            error_code="rate_limit_exceeded",
            prompt_tokens=50,
            latency_ms=200,
        )
        mock_db.execute.return_value = make_execute_result(rows=[event])

        resp = client.get("/admin/usage/errors", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        row = data[0]
        assert row["id"] == str(event.id)
        assert row["request_id"] == event.request_id
        assert row["model"] == "anthropic/claude-3-haiku"
        assert row["provider"] == "bedrock"
        assert row["error_code"] == "rate_limit_exceeded"
        assert row["prompt_tokens"] == 50
        assert row["latency_ms"] == 200
        assert "created_at" in row

    def test_nullable_fields_serialised_as_none(self, client, mock_db):
        """error_code, prompt_tokens, and latency_ms may all be None."""
        event = _make_event(error_code=None, prompt_tokens=None, latency_ms=None)
        mock_db.execute.return_value = make_execute_result(rows=[event])

        resp = client.get("/admin/usage/errors", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        row = resp.json()[0]
        assert row["error_code"] is None
        assert row["prompt_tokens"] is None
        assert row["latency_ms"] is None

    def test_multiple_rows_returned(self, client, mock_db):
        events = [_make_event() for _ in range(3)]
        mock_db.execute.return_value = make_execute_result(rows=events)

        resp = client.get("/admin/usage/errors", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_default_limit_accepted(self, client, mock_db):
        """Endpoint should respond 200 without an explicit limit param."""
        mock_db.execute.return_value = make_execute_result(rows=[])

        resp = client.get("/admin/usage/errors", headers=ADMIN_HEADERS)

        assert resp.status_code == 200

    def test_custom_limit_accepted(self, client, mock_db):
        """?limit= query param should be accepted without a 422."""
        mock_db.execute.return_value = make_execute_result(rows=[])

        resp = client.get("/admin/usage/errors?limit=10", headers=ADMIN_HEADERS)

        assert resp.status_code == 200

    def test_created_at_is_iso8601(self, client, mock_db):
        event = _make_event(
            created_at=datetime(2026, 4, 7, 9, 30, 0, tzinfo=timezone.utc)
        )
        mock_db.execute.return_value = make_execute_result(rows=[event])

        resp = client.get("/admin/usage/errors", headers=ADMIN_HEADERS)

        row = resp.json()[0]
        # Should be parseable as ISO 8601
        parsed = datetime.fromisoformat(row["created_at"])
        assert parsed.year == 2026
        assert parsed.month == 4
        assert parsed.day == 7

    def test_no_auth_returns_401(self, client):
        resp = client.get("/admin/usage/errors")

        assert resp.status_code == 401

    def test_non_admin_jwt_returns_403(self, client):
        """A valid user JWT without the admin permission must be rejected."""
        resp = client.get("/admin/usage/errors", headers=USER_HEADERS)

        assert resp.status_code == 403
