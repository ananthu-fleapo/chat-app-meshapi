"""
Tests for discount admin endpoints — POST, GET, PATCH /admin/discounts.

Covers:
  create_discount  — happy path, conflict 409, valid_from passthrough
  update_discount  — label-only update, valid_from edit, expire (ended_at/ended_reason stamped)
  list_discounts   — no filter, user_id filter, model_id filter
"""

import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as _jwt
import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET, make_execute_result


# ── Admin JWT ─────────────────────────────────────────────────────────────────

def make_admin_jwt() -> str:
    now = int(time.time())
    return _jwt.encode(
        {
            "sub": "admin-001",
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
    session.refresh = AsyncMock()
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

    with patch("app.routers.admin.get_redis", return_value=None):
        yield TestClient(app, raise_server_exceptions=True)


def _make_discount_orm(
    discount_pct: str = "20.00",
    user_id: str | None = "user-123",
    model_id: str | None = "openai/gpt-4o",
    valid_from_offset: int = -1,   # days relative to now; negative = past
    valid_until: datetime | None = None,
    ended_at: datetime | None = None,
    ended_reason: str | None = None,
    label: str | None = None,
) -> MagicMock:
    """Build a Discount ORM-like mock."""
    d = MagicMock()
    d.id = uuid.uuid4()
    d.user_id = user_id
    d.model_id = model_id
    d.discount_pct = Decimal(discount_pct)
    d.valid_from = datetime.now(UTC) + timedelta(days=valid_from_offset)
    d.valid_until = valid_until
    d.ended_at = ended_at
    d.ended_reason = ended_reason
    d.label = label
    d.created_at = datetime.now(UTC) - timedelta(days=10)
    return d


# ── POST /admin/discounts ─────────────────────────────────────────────────────

class TestCreateDiscount:

    def test_creates_discount_successfully(self, client, mock_db):
        """Happy path: no conflict → 201 with discount data."""
        mock_db.execute.side_effect = [
            make_execute_result(rows=[]),   # conflict check: no conflicts
        ]

        # Populate server-default fields (id, created_at) that the DB would set
        def _refresh(d):
            import uuid as _uuid
            from datetime import UTC, datetime
            if d.id is None:
                d.id = _uuid.uuid4()
            if d.created_at is None:
                d.created_at = datetime.now(UTC)

        mock_db.refresh.side_effect = _refresh

        resp = client.post(
            "/admin/discounts",
            json={"user_id": "user-123", "model_id": "openai/gpt-4o", "discount_pct": 20},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["discount_pct"] == "20.0"
        assert data["user_id"] == "user-123"

    def test_conflict_returns_409(self, client, mock_db):
        """Active discount with same scope key → 409 with conflicts list."""
        existing = _make_discount_orm(discount_pct="10.00")

        mock_db.execute.return_value = make_execute_result(rows=[], scalar=existing)
        # scalars().all() returns the conflict
        conflict_result = MagicMock()
        conflict_result.scalars.return_value.all.return_value = [existing]
        mock_db.execute.return_value = conflict_result

        resp = client.post(
            "/admin/discounts",
            json={"user_id": "user-123", "model_id": "openai/gpt-4o", "discount_pct": 20},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert "conflicts" in detail
        assert len(detail["conflicts"]) == 1

    def test_missing_both_user_and_model_creates_global_discount(self, client, mock_db):
        """No user_id AND no model_id = global discount. Should return 201."""
        mock_db.execute.side_effect = [
            make_execute_result(rows=[]),   # conflict check: no conflicts
        ]

        def _refresh(d):
            import uuid as _uuid
            from datetime import UTC, datetime
            if d.id is None:
                d.id = _uuid.uuid4()
            if d.created_at is None:
                d.created_at = datetime.now(UTC)

        mock_db.refresh.side_effect = _refresh

        resp = client.post(
            "/admin/discounts",
            json={"discount_pct": 10},
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] is None
        assert data["model_id"] is None
        assert data["discount_pct"] == "10.0"

    def test_discount_pct_out_of_range_returns_422(self, client, mock_db):
        """discount_pct > 100 → 422."""
        mock_db.execute.return_value = make_execute_result(rows=[])
        resp = client.post(
            "/admin/discounts",
            json={"user_id": "user-123", "discount_pct": 150},
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 422

    def test_valid_from_accepted_when_provided(self, client, mock_db):
        """valid_from in the payload is accepted and not ignored."""
        future = (datetime.now(UTC) + timedelta(days=2)).isoformat()

        mock_db.execute.side_effect = [make_execute_result(rows=[])]

        def _refresh(d):
            import uuid as _uuid
            from datetime import UTC, datetime
            if d.id is None:
                d.id = _uuid.uuid4()
            if d.created_at is None:
                d.created_at = datetime.now(UTC)

        mock_db.refresh.side_effect = _refresh

        client.post(
            "/admin/discounts",
            json={"user_id": "user-123", "discount_pct": 10, "valid_from": future},
            headers=ADMIN_HEADERS,
        )

        # valid_from was passed through to the Discount constructor (not overwritten by now())
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.valid_from is not None
        assert added_obj.valid_from > datetime.now(UTC)

    def test_model_only_discount_accepted(self, client, mock_db):
        """model_id without user_id (global model discount) is valid."""
        mock_db.execute.side_effect = [make_execute_result(rows=[])]

        def _refresh(d):
            import uuid as _uuid
            from datetime import UTC, datetime
            if d.id is None:
                d.id = _uuid.uuid4()
            if d.created_at is None:
                d.created_at = datetime.now(UTC)

        mock_db.refresh.side_effect = _refresh

        resp = client.post(
            "/admin/discounts",
            json={"model_id": "openai/gpt-4o", "discount_pct": 15},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 201


# ── PATCH /admin/discounts/{id} ───────────────────────────────────────────────

class TestUpdateDiscount:

    def test_expire_stamps_ended_at_and_reason(self, client, mock_db):
        """Setting valid_until to now/past stamps ended_at and ended_reason=disabled."""
        discount = _make_discount_orm()
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()

        resp = client.patch(
            f"/admin/discounts/{discount.id}",
            json={"valid_until": past, "ended_reason": "disabled"},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 200
        # ended_at and ended_reason should have been set on the ORM object
        assert discount.ended_at is not None
        assert discount.ended_reason == "disabled"

    def test_expire_with_replaced_reason(self, client, mock_db):
        """ended_reason='replaced' is accepted and stored."""
        discount = _make_discount_orm()
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()

        client.patch(
            f"/admin/discounts/{discount.id}",
            json={"valid_until": past, "ended_reason": "replaced"},
            headers=ADMIN_HEADERS,
        )

        assert discount.ended_reason == "replaced"

    def test_future_valid_until_does_not_stamp_ended_at(self, client, mock_db):
        """Setting valid_until to a future date does NOT stamp ended_at."""
        discount = _make_discount_orm()
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        future = (datetime.now(UTC) + timedelta(days=30)).isoformat()

        client.patch(
            f"/admin/discounts/{discount.id}",
            json={"valid_until": future},
            headers=ADMIN_HEADERS,
        )

        assert discount.ended_at is None

    def test_label_only_update(self, client, mock_db):
        """Updating only label leaves discount_pct and dates unchanged."""
        discount = _make_discount_orm(discount_pct="25.00")
        original_pct = discount.discount_pct
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        client.patch(
            f"/admin/discounts/{discount.id}",
            json={"label": "Q3 promo"},
            headers=ADMIN_HEADERS,
        )

        assert discount.label == "Q3 promo"
        assert discount.discount_pct == original_pct  # unchanged

    def test_valid_from_update_for_future_discount(self, client, mock_db):
        """valid_from can be updated via PATCH (for future discounts)."""
        discount = _make_discount_orm(valid_from_offset=5)  # scheduled in the future
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        new_start = (datetime.now(UTC) + timedelta(days=10)).isoformat()

        client.patch(
            f"/admin/discounts/{discount.id}",
            json={"valid_from": new_start},
            headers=ADMIN_HEADERS,
        )

        # valid_from should have been updated
        assert discount.valid_from is not None

    def test_not_found_returns_404(self, client, mock_db):
        """Non-existent discount → 404."""
        mock_db.execute.return_value = make_execute_result(scalar=None)

        resp = client.patch(
            f"/admin/discounts/{uuid.uuid4()}",
            json={"label": "test"},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 404

    def test_cannot_edit_discount_pct_after_started(self, client, mock_db):
        """Changing discount_pct on an already-started discount → 422."""
        discount = _make_discount_orm(valid_from_offset=-1)  # started 1 day ago
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        resp = client.patch(
            f"/admin/discounts/{discount.id}",
            json={"discount_pct": 30},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 422

    def test_cannot_edit_valid_from_after_started(self, client, mock_db):
        """Changing valid_from on an already-started discount → 422."""
        discount = _make_discount_orm(valid_from_offset=-1)  # started 1 day ago
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        new_start = (datetime.now(UTC) - timedelta(days=2)).isoformat()

        resp = client.patch(
            f"/admin/discounts/{discount.id}",
            json={"valid_from": new_start},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 422

    def test_can_edit_discount_pct_before_started(self, client, mock_db):
        """discount_pct is editable on a future-scheduled (not yet started) discount."""
        discount = _make_discount_orm(valid_from_offset=5)  # starts 5 days from now
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        resp = client.patch(
            f"/admin/discounts/{discount.id}",
            json={"discount_pct": 30},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 200

    def test_clear_valid_until_via_patch(self, client, mock_db):
        """PATCH with valid_until: null should clear the expiry (set DB col to NULL)."""
        discount = _make_discount_orm(valid_until=datetime.now(UTC) + timedelta(days=10))
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        resp = client.patch(
            f"/admin/discounts/{discount.id}",
            json={"valid_until": None},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 200
        assert discount.valid_until is None

    def test_invalid_ended_reason_returns_422(self, client, mock_db):
        """Unknown ended_reason value → 422 validation error."""
        discount = _make_discount_orm()
        mock_db.execute.return_value = make_execute_result(scalar=discount)

        past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()

        resp = client.patch(
            f"/admin/discounts/{discount.id}",
            json={"valid_until": past, "ended_reason": "invalid_reason"},
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 422


# ── GET /admin/discounts ──────────────────────────────────────────────────────

class TestListDiscounts:

    def test_list_all_returns_discounts(self, client, mock_db):
        """No filter → returns all discounts."""
        d1 = _make_discount_orm(user_id="user-a")
        d2 = _make_discount_orm(user_id="user-b")
        result = MagicMock()
        result.scalars.return_value.all.return_value = [d1, d2]
        mock_db.execute.return_value = result

        resp = client.get("/admin/discounts", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_filter_by_user_id(self, client, mock_db):
        """?user_id= filters results to that user."""
        d = _make_discount_orm(user_id="user-x")
        result = MagicMock()
        result.scalars.return_value.all.return_value = [d]
        mock_db.execute.return_value = result

        resp = client.get("/admin/discounts?user_id=user-x", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["user_id"] == "user-x"

    def test_filter_by_model_id(self, client, mock_db):
        """?model_id= filters results to that model."""
        d = _make_discount_orm(model_id="anthropic/claude-3-5-sonnet")
        result = MagicMock()
        result.scalars.return_value.all.return_value = [d]
        mock_db.execute.return_value = result

        resp = client.get(
            "/admin/discounts?model_id=anthropic/claude-3-5-sonnet",
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()[0]["model_id"] == "anthropic/claude-3-5-sonnet"

    def test_empty_list_returns_empty_array(self, client, mock_db):
        """No discounts → empty array, not 404."""
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result

        resp = client.get("/admin/discounts", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated_returns_401(self, client):
        """Missing auth header → 401."""
        resp = client.get("/admin/discounts")
        assert resp.status_code == 401
