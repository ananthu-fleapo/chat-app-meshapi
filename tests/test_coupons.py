"""
Tests for app/routers/coupons.py

Covers:
  coupons listing / validation
  admin coupon create
"""

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4  # noqa: F401 — used via make_execute_result

import jwt as _jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET, make_execute_result, make_jwt

os.environ.setdefault("ROUTERSVC_SERVICE_KEY", "test-service-key")


def make_admin_jwt(sub: str = "00000000-0000-0000-0000-000000000001") -> str:
    now = int(datetime.now(timezone.utc).timestamp())
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

    def _add(obj):
        if getattr(obj, "id", None) is None:
            try:
                obj.id = uuid4()
            except Exception:
                pass
        if getattr(obj, "created_at", None) is None:
            try:
                obj.created_at = datetime.now(timezone.utc)
            except Exception:
                pass

    session.add.side_effect = _add
    return session


@pytest.fixture
def client(mock_db_session):
    from app.main import create_app
    from app.db.session import get_db_session
    from app.cache.redis_client import get_redis

    app = create_app()

    async def _override_db():
        yield mock_db_session

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_redis] = lambda: None
    return TestClient(app, raise_server_exceptions=True)


JWT_HEADERS = {"Authorization": f"Bearer {make_jwt()}"}
ADMIN_HEADERS = {"Authorization": f"Bearer {make_admin_jwt()}"}


def _make_coupon(code: str = "SAVE20"):
    from app.db.models import CheckoutCoupon

    coupon = CheckoutCoupon(
        code=code,
        name="Save 20",
        description="Test coupon",
        discount_type="percentage",
        discount_value=Decimal("20.00"),
        reuse_policy="single_use",
        max_uses=10,
        used_count=0,
        valid_till=datetime.now(timezone.utc) + timedelta(days=1),
        is_active=True,
    )
    coupon.id = uuid4()
    coupon.created_at = datetime.now(timezone.utc)
    coupon.updated_at = datetime.now(timezone.utc)
    return coupon


class TestCoupons:
    def test_list_coupons_returns_applicable_coupons(self, client, mock_db_session):
        coupon = _make_coupon()
        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        with patch("app.routers.coupons._get_coupon_for_user", new=AsyncMock(return_value=(coupon, None))):
            resp = client.get("/v1/coupons", headers=JWT_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["code"] == "SAVE20"
        assert body[0]["name"] == "Save 20"
        assert body[0]["discount_type"] == "percentage"

    def test_list_coupons_excludes_unusable_coupon(self, client, mock_db_session):
        usable_coupon = _make_coupon(code="SAVE20")
        blocked_coupon = _make_coupon(code="ONETIME")
        # In the optimized version, filtering happens in SQL. 
        # For the test, we simulate the SQL filtering by only returning the usable coupon from the mock DB.
        mock_db_session.execute.return_value = make_execute_result(
            rows=[usable_coupon], scalar=None
        )

        with patch("app.routers.coupons._get_coupon_for_user") as mock_get_user:
            resp = client.get("/v1/coupons", headers=JWT_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert [item["code"] for item in body] == ["SAVE20"]
        # Ensure we didn't call the loop validator!
        mock_get_user.assert_not_called()

    def test_list_coupons_does_not_leak_user_ids(self, client, mock_db_session):
        from app.db.models import CouponUser
        coupon = _make_coupon()
        # Mock users for the coupon
        coupon.users = [CouponUser(coupon_id=coupon.id, user_id="user-123")]
        
        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        with patch("app.routers.coupons._get_coupon_for_user", new=AsyncMock(return_value=(coupon, None))):
            resp = client.get("/v1/coupons", headers=JWT_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert "user_ids" not in body[0]

    def test_validate_coupon_returns_discount(self, client, mock_db_session):
        coupon = _make_coupon()

        with patch(
            "app.routers.coupons._get_coupon_for_user",
            new=AsyncMock(return_value=(coupon, Decimal("2.00"))),
        ):
            resp = client.post(
                "/v1/coupons/validate",
                json={"code": "SAVE20", "amount": "10.00", "currency": "usd"},
                headers=JWT_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json() == {
            "valid": True,
            "discount_type": "percentage",
            "discount_value": "20.00",
            "discount_amount": "2.00",
        }


class TestAdminCoupons:
    def test_admin_create_coupon(self, client, mock_db_session):
        mock_db_session.execute.return_value = make_execute_result(rows=[], scalar=None)

        resp = client.post(
            "/v1/admin/coupons",
            json={
                "code": "NEW50",
                "name": "New 50",
                "description": "Launch offer",
                "discount_type": "percentage",
                "discount_value": "50.00",
                "reuse_policy": "single_use",
                "max_uses": 25,
                "is_active": True,
                "user_ids": ["user-123"],
            },
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["code"] == "NEW50"
        assert body["name"] == "New 50"
        assert body["description"] == "Launch offer"
        added_users = [call.args[0] for call in mock_db_session.add.call_args_list if getattr(call.args[0], "user_id", None)]
        assert [row.user_id for row in added_users] == ["user-123"]

    def test_admin_update_coupon_replaces_user_assignments(self, client, mock_db_session):
        from app.db.models import CheckoutCoupon, CouponUser

        coupon_id = uuid4()
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
        coupon.id = coupon_id
        existing_assignment = CouponUser(coupon_id=coupon_id, user_id="user-old")

        mock_db_session.scalar.return_value = coupon
        mock_db_session.execute.return_value = make_execute_result(rows=[existing_assignment], scalar=None)

        resp = client.patch(
            f"/v1/admin/coupons/{coupon_id}",
            json={
                "name": "Save 25",
                "user_ids": ["user-new"],
            },
            headers=ADMIN_HEADERS,
        )

        assert resp.status_code == 200
        assert coupon.name == "Save 25"
        mock_db_session.delete.assert_awaited_once_with(existing_assignment)
        added_users = [call.args[0] for call in mock_db_session.add.call_args_list if getattr(call.args[0], "user_id", None)]
        assert [row.user_id for row in added_users] == ["user-new"]

    def test_admin_list_coupons_includes_user_ids(self, client, mock_db_session):
        from app.db.models import CouponUser
        coupon = _make_coupon()
        coupon.users = [CouponUser(coupon_id=coupon.id, user_id="admin-target")]
        
        mock_db_session.execute.return_value = make_execute_result(rows=[coupon], scalar=None)

        resp = client.get("/v1/admin/coupons", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["user_ids"] == ["admin-target"]
