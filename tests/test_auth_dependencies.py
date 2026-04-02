"""
Unit tests for app/auth/dependencies.py

Covers:
  _extract_bearer         — valid header, missing/malformed header, empty token
  _hash_key               — deterministic SHA-256 hex
  _check_active           — active key passes, suspended key raises ForbiddenError
  get_authenticated_key   — cache hit, cache miss+DB hit, cache miss+DB miss, suspended
  verify_webhook_key      — correct secret, wrong secret, no WEBHOOK_API_KEY configured
  get_any_auth_owner      — no credentials, JWT success, JWT→API key fallback paths
"""

import hashlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_execute_result
from app.exceptions import ForbiddenError, UnauthorizedError


# ── _extract_bearer ────────────────────────────────────────────────────────────

class TestExtractBearer:

    def test_valid_header_returns_token(self):
        from app.auth.dependencies import _extract_bearer
        assert _extract_bearer("Bearer mytoken123") == "mytoken123"

    def test_missing_header_raises_unauthorized(self):
        from app.auth.dependencies import _extract_bearer
        with pytest.raises(UnauthorizedError):
            _extract_bearer("")

    def test_none_header_raises_unauthorized(self):
        from app.auth.dependencies import _extract_bearer
        with pytest.raises(UnauthorizedError):
            _extract_bearer(None)

    def test_non_bearer_prefix_raises_unauthorized(self):
        from app.auth.dependencies import _extract_bearer
        with pytest.raises(UnauthorizedError):
            _extract_bearer("Token mytoken123")

    def test_empty_token_after_bearer_raises_unauthorized(self):
        from app.auth.dependencies import _extract_bearer
        with pytest.raises(UnauthorizedError):
            _extract_bearer("Bearer   ")


# ── _hash_key ─────────────────────────────────────────────────────────────────

class TestHashKey:

    def test_produces_sha256_hex(self):
        from app.auth.dependencies import _hash_key
        raw = "testkey"
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert _hash_key(raw) == expected

    def test_deterministic(self):
        from app.auth.dependencies import _hash_key
        assert _hash_key("abc") == _hash_key("abc")

    def test_different_inputs_produce_different_hashes(self):
        from app.auth.dependencies import _hash_key
        assert _hash_key("abc") != _hash_key("xyz")


# ── _check_active ─────────────────────────────────────────────────────────────

class TestCheckActive:

    def test_active_key_does_not_raise(self):
        from app.auth.dependencies import _check_active
        key = MagicMock()
        key.status = "active"
        _check_active(key, "raw")  # must not raise

    def test_suspended_key_raises_forbidden(self):
        from app.auth.dependencies import _check_active
        key = MagicMock()
        key.status = "suspended"
        key.id = uuid.uuid4()
        key.owner = "test-owner"
        with patch("app.metrics.AUTH_FAILURES", MagicMock()):
            with pytest.raises(ForbiddenError):
                _check_active(key, "raw")


# ── get_authenticated_key ─────────────────────────────────────────────────────

class TestGetAuthenticatedKey:

    async def test_cache_hit_returns_key_without_db_call(self, mock_db):
        """Cache hit path: returns key immediately, no Postgres query."""
        from app.auth.dependencies import get_authenticated_key

        cached_key = MagicMock()
        cached_key.status = "active"
        cached_key.id = uuid.uuid4()
        cached_key.owner = "acme"

        with patch("app.auth.dependencies.get_cached_key", AsyncMock(return_value=cached_key)):
            result = await get_authenticated_key(
                authorization="Bearer validtoken",
                db=mock_db,
            )

        assert result is cached_key
        mock_db.execute.assert_not_called()

    async def test_cache_miss_db_hit_returns_key_and_populates_cache(self, mock_db):
        """Cache miss → DB hit: key is returned and cached for next request."""
        from app.auth.dependencies import get_authenticated_key

        db_key = MagicMock()
        db_key.status = "active"
        db_key.id = uuid.uuid4()
        db_key.owner = "acme"
        db_key.key_hash = "somehash"
        mock_db.execute.return_value = make_execute_result(scalar=db_key)

        with patch("app.auth.dependencies.get_cached_key", AsyncMock(return_value=None)), \
             patch("app.auth.dependencies.set_cached_key", AsyncMock()) as mock_set:
            result = await get_authenticated_key(
                authorization="Bearer validtoken",
                db=mock_db,
            )

        assert result is db_key
        mock_set.assert_called_once_with(db_key)

    async def test_cache_miss_db_miss_raises_unauthorized(self, mock_db):
        """Cache miss + DB miss → 401."""
        from app.auth.dependencies import get_authenticated_key

        mock_db.execute.return_value = make_execute_result(scalar=None)

        with patch("app.auth.dependencies.get_cached_key", AsyncMock(return_value=None)), \
             patch("app.metrics.AUTH_FAILURES", MagicMock()):
            with pytest.raises(UnauthorizedError):
                await get_authenticated_key(
                    authorization="Bearer unknowntoken",
                    db=mock_db,
                )

    async def test_suspended_key_from_db_raises_forbidden(self, mock_db):
        """DB returns a suspended key → 403."""
        from app.auth.dependencies import get_authenticated_key

        db_key = MagicMock()
        db_key.status = "suspended"
        db_key.id = uuid.uuid4()
        db_key.owner = "acme"
        mock_db.execute.return_value = make_execute_result(scalar=db_key)

        with patch("app.auth.dependencies.get_cached_key", AsyncMock(return_value=None)), \
             patch("app.auth.dependencies.set_cached_key", AsyncMock()), \
             patch("app.metrics.AUTH_FAILURES", MagicMock()):
            with pytest.raises(ForbiddenError):
                await get_authenticated_key(
                    authorization="Bearer validtoken",
                    db=mock_db,
                )

    async def test_suspended_key_from_cache_raises_forbidden(self, mock_db):
        """Cache returns a suspended key → 403 (no DB call needed)."""
        from app.auth.dependencies import get_authenticated_key

        cached_key = MagicMock()
        cached_key.status = "suspended"
        cached_key.id = uuid.uuid4()
        cached_key.owner = "acme"

        with patch("app.auth.dependencies.get_cached_key", AsyncMock(return_value=cached_key)), \
             patch("app.metrics.AUTH_FAILURES", MagicMock()):
            with pytest.raises(ForbiddenError):
                await get_authenticated_key(
                    authorization="Bearer validtoken",
                    db=mock_db,
                )


# ── verify_webhook_key ────────────────────────────────────────────────────────

class TestVerifyWebhookKey:

    async def test_correct_secret_does_not_raise(self):
        """Matching WEBHOOK_API_KEY → passes."""
        from app.auth.dependencies import verify_webhook_key
        # conftest sets WEBHOOK_API_KEY = "test-webhook-secret"
        await verify_webhook_key(authorization="Bearer test-webhook-secret")

    async def test_wrong_secret_raises_unauthorized(self):
        """Wrong token → 401."""
        from app.auth.dependencies import verify_webhook_key
        with pytest.raises(UnauthorizedError):
            await verify_webhook_key(authorization="Bearer wrong-secret")

    async def test_no_webhook_key_configured_raises_forbidden(self):
        """Server has no WEBHOOK_API_KEY set → 403."""
        from app.auth.dependencies import verify_webhook_key
        with patch("app.auth.dependencies.settings") as mock_settings:
            mock_settings.webhook_api_key = None
            with pytest.raises(ForbiddenError):
                await verify_webhook_key(authorization="Bearer test-webhook-secret")


# ── get_any_auth_owner ────────────────────────────────────────────────────────

def _make_credentials(token: str):
    """Build a mock HTTPAuthorizationCredentials with the given bearer token."""
    creds = MagicMock()
    creds.credentials = token
    return creds


class TestGetAnyAuthOwner:

    async def test_no_credentials_raises_unauthorized(self, mock_db):
        """Missing Authorization header → 401."""
        from app.auth.dependencies import get_any_auth_owner
        with pytest.raises(UnauthorizedError):
            await get_any_auth_owner(credentials=None, db=mock_db)

    async def test_jwt_dev_bypass_returns_token_as_owner(self, mock_db):
        """
        With SUPABASE_JWT_SECRET unset (dev bypass), any bearer string is
        accepted as the owner — DB is never touched.
        """
        from app.auth.dependencies import get_any_auth_owner
        owner = await get_any_auth_owner(
            credentials=_make_credentials("acme-corp"),
            db=mock_db,
        )
        assert owner == "acme-corp"
        mock_db.execute.assert_not_called()

    async def test_jwt_fails_falls_back_to_api_key_cache_hit(self, mock_db):
        """JWT auth fails → falls back to API key; cache hit returns owner."""
        from app.auth.dependencies import get_any_auth_owner

        cached_key = MagicMock()
        cached_key.status = "active"
        cached_key.id = uuid.uuid4()
        cached_key.owner = "key-owner"

        with patch(
            "app.auth.control_plane.get_control_plane_user",
            AsyncMock(side_effect=UnauthorizedError()),
        ), patch(
            "app.auth.dependencies.get_cached_key",
            AsyncMock(return_value=cached_key),
        ):
            owner = await get_any_auth_owner(
                credentials=_make_credentials("rsk_someapikey"),
                db=mock_db,
            )

        assert owner == "key-owner"
        mock_db.execute.assert_not_called()

    async def test_jwt_fails_falls_back_to_api_key_db_hit(self, mock_db):
        """JWT auth fails → cache miss → DB hit returns owner and populates cache."""
        from app.auth.dependencies import get_any_auth_owner

        db_key = MagicMock()
        db_key.status = "active"
        db_key.id = uuid.uuid4()
        db_key.owner = "db-owner"
        mock_db.execute.return_value = make_execute_result(scalar=db_key)

        with patch(
            "app.auth.control_plane.get_control_plane_user",
            AsyncMock(side_effect=UnauthorizedError()),
        ), patch(
            "app.auth.dependencies.get_cached_key",
            AsyncMock(return_value=None),
        ), patch(
            "app.auth.dependencies.set_cached_key",
            AsyncMock(),
        ) as mock_set:
            owner = await get_any_auth_owner(
                credentials=_make_credentials("rsk_someapikey"),
                db=mock_db,
            )

        assert owner == "db-owner"
        mock_set.assert_called_once_with(db_key)

    async def test_jwt_fails_api_key_not_found_raises_unauthorized(self, mock_db):
        """JWT auth fails + key not in cache or DB → 401."""
        from app.auth.dependencies import get_any_auth_owner

        mock_db.execute.return_value = make_execute_result(scalar=None)

        with patch(
            "app.auth.control_plane.get_control_plane_user",
            AsyncMock(side_effect=UnauthorizedError()),
        ), patch(
            "app.auth.dependencies.get_cached_key",
            AsyncMock(return_value=None),
        ):
            with pytest.raises(UnauthorizedError):
                await get_any_auth_owner(
                    credentials=_make_credentials("rsk_unknownkey"),
                    db=mock_db,
                )

    async def test_jwt_fails_suspended_api_key_raises_forbidden(self, mock_db):
        """JWT auth fails → DB returns a suspended key → 403."""
        from app.auth.dependencies import get_any_auth_owner

        db_key = MagicMock()
        db_key.status = "suspended"
        db_key.id = uuid.uuid4()
        db_key.owner = "suspended-owner"
        mock_db.execute.return_value = make_execute_result(scalar=db_key)

        with patch(
            "app.auth.control_plane.get_control_plane_user",
            AsyncMock(side_effect=UnauthorizedError()),
        ), patch(
            "app.auth.dependencies.get_cached_key",
            AsyncMock(return_value=None),
        ), patch(
            "app.auth.dependencies.set_cached_key",
            AsyncMock(),
        ), patch("app.metrics.AUTH_FAILURES", MagicMock()):
            with pytest.raises(ForbiddenError):
                await get_any_auth_owner(
                    credentials=_make_credentials("rsk_suspendedkey"),
                    db=mock_db,
                )

    async def test_jwt_fails_suspended_api_key_in_cache_raises_forbidden(self, mock_db):
        """JWT auth fails → cache returns a suspended key → 403, no DB call."""
        from app.auth.dependencies import get_any_auth_owner

        cached_key = MagicMock()
        cached_key.status = "suspended"
        cached_key.id = uuid.uuid4()
        cached_key.owner = "suspended-owner"

        with patch(
            "app.auth.control_plane.get_control_plane_user",
            AsyncMock(side_effect=UnauthorizedError()),
        ), patch(
            "app.auth.dependencies.get_cached_key",
            AsyncMock(return_value=cached_key),
        ), patch("app.metrics.AUTH_FAILURES", MagicMock()):
            with pytest.raises(ForbiddenError):
                await get_any_auth_owner(
                    credentials=_make_credentials("rsk_suspendedkey"),
                    db=mock_db,
                )

        mock_db.execute.assert_not_called()
