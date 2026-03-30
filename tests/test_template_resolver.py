"""
Unit tests for app/templates/resolver.py

Covers:
  _is_uuid         — valid UUID string returns True, non-UUID name returns False
  resolve_template — UUID lookup found, UUID lookup not found (falls through to name),
                     name lookup found, name lookup not found (NotFoundError)
"""

import uuid
from unittest.mock import MagicMock

import pytest

from tests.conftest import make_execute_result

OWNER = "acme"
VALID_UUID = "00000000-0000-0000-0000-000000000001"


# ── _is_uuid ──────────────────────────────────────────────────────────────────

class TestIsUuid:

    def test_valid_uuid_returns_true(self):
        from app.templates.resolver import _is_uuid
        assert _is_uuid(VALID_UUID) is True

    def test_name_string_returns_false(self):
        from app.templates.resolver import _is_uuid
        assert _is_uuid("my-template-name") is False

    def test_partial_uuid_returns_false(self):
        from app.templates.resolver import _is_uuid
        assert _is_uuid("00000000-0000-0000-0000") is False

    def test_empty_string_returns_false(self):
        from app.templates.resolver import _is_uuid
        assert _is_uuid("") is False


# ── resolve_template ──────────────────────────────────────────────────────────

class TestResolveTemplate:

    async def test_uuid_input_found_returns_template(self, mock_db):
        """UUID-format input that resolves in DB → returns the template."""
        from app.templates.resolver import resolve_template

        template = MagicMock()
        mock_db.execute.return_value = make_execute_result(scalar=template)

        result = await resolve_template(VALID_UUID, OWNER, mock_db)
        assert result is template

    async def test_uuid_input_not_found_falls_through_to_name_lookup(self, mock_db):
        """UUID miss → falls through to name-based lookup with (owner, name)."""
        from app.templates.resolver import resolve_template
        from app.exceptions import NotFoundError

        # UUID lookup returns None, name lookup also returns None → 404
        mock_db.execute.side_effect = [
            make_execute_result(scalar=None),  # UUID lookup: miss
            make_execute_result(scalar=None),  # name lookup: miss
        ]

        with pytest.raises(NotFoundError):
            await resolve_template(VALID_UUID, OWNER, mock_db)

        assert mock_db.execute.call_count == 2

    async def test_name_input_found_returns_template(self, mock_db):
        """Non-UUID name input resolved by (owner, name) → returns template."""
        from app.templates.resolver import resolve_template

        template = MagicMock()
        mock_db.execute.return_value = make_execute_result(scalar=template)

        result = await resolve_template("my-template", OWNER, mock_db)
        assert result is template

    async def test_name_input_not_found_raises_not_found(self, mock_db):
        """Name not found in owner's namespace → NotFoundError."""
        from app.templates.resolver import resolve_template
        from app.exceptions import NotFoundError

        mock_db.execute.return_value = make_execute_result(scalar=None)

        with pytest.raises(NotFoundError):
            await resolve_template("missing-template", OWNER, mock_db)

    async def test_name_lookup_is_owner_scoped(self, mock_db):
        """Name lookup executes exactly one DB query (no UUID path taken)."""
        from app.templates.resolver import resolve_template
        from app.exceptions import NotFoundError

        mock_db.execute.return_value = make_execute_result(scalar=None)

        with pytest.raises(NotFoundError):
            await resolve_template("some-name", OWNER, mock_db)

        # Only one execute call: the name+owner query
        mock_db.execute.assert_called_once()

    async def test_uuid_found_skips_name_lookup(self, mock_db):
        """UUID hit → name lookup is never performed."""
        from app.templates.resolver import resolve_template

        template = MagicMock()
        mock_db.execute.return_value = make_execute_result(scalar=template)

        await resolve_template(VALID_UUID, OWNER, mock_db)

        # Only one execute call: the UUID query
        mock_db.execute.assert_called_once()
