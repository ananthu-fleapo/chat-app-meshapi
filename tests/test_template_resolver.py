"""
Unit tests for app/templates/resolver.py

Covers:
  _is_uuid         — valid UUID string returns True, non-UUID name returns False
  resolve_template — UUID lookup (found / miss), name lookup (found / miss),
                     global fallback (found / miss), priority ordering,
                     owner isolation
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
        """UUID miss → falls through to name-based lookup, then global fallback."""
        from app.templates.resolver import resolve_template
        from app.exceptions import NotFoundError

        # UUID lookup → miss, owner-name lookup → miss, global fallback → miss → 404
        mock_db.execute.side_effect = [
            make_execute_result(scalar=None),  # UUID lookup: miss
            make_execute_result(scalar=None),  # name+owner lookup: miss
            make_execute_result(scalar=None),  # global fallback: miss
        ]

        with pytest.raises(NotFoundError):
            await resolve_template(VALID_UUID, OWNER, mock_db)

        assert mock_db.execute.call_count == 3

    async def test_name_input_found_returns_template(self, mock_db):
        """Non-UUID name input resolved by (owner, name) → returns template."""
        from app.templates.resolver import resolve_template

        template = MagicMock()
        mock_db.execute.return_value = make_execute_result(scalar=template)

        result = await resolve_template("my-template", OWNER, mock_db)
        assert result is template

    async def test_name_input_not_found_raises_not_found(self, mock_db):
        """Name not found in owner's namespace or globals → NotFoundError."""
        from app.templates.resolver import resolve_template
        from app.exceptions import NotFoundError

        mock_db.execute.side_effect = [
            make_execute_result(scalar=None),  # name+owner lookup: miss
            make_execute_result(scalar=None),  # global fallback: miss
        ]

        with pytest.raises(NotFoundError):
            await resolve_template("missing-template", OWNER, mock_db)

    async def test_name_lookup_falls_back_to_global(self, mock_db):
        """Name miss in owner namespace → global fallback → returns global template."""
        from app.templates.resolver import resolve_template

        global_template = MagicMock()
        mock_db.execute.side_effect = [
            make_execute_result(scalar=None),           # name+owner lookup: miss
            make_execute_result(scalar=global_template), # global fallback: hit
        ]

        result = await resolve_template("shared-prompt", OWNER, mock_db)
        assert result is global_template
        assert mock_db.execute.call_count == 2

    async def test_name_lookup_is_owner_scoped(self, mock_db):
        """Name lookup tries owner-scoped query first, then global fallback."""
        from app.templates.resolver import resolve_template
        from app.exceptions import NotFoundError

        mock_db.execute.side_effect = [
            make_execute_result(scalar=None),  # name+owner lookup: miss
            make_execute_result(scalar=None),  # global fallback: miss
        ]

        with pytest.raises(NotFoundError):
            await resolve_template("some-name", OWNER, mock_db)

        # Two execute calls: owner-scoped name query + global fallback
        assert mock_db.execute.call_count == 2

    async def test_uuid_found_skips_name_lookup(self, mock_db):
        """UUID hit → name lookup is never performed."""
        from app.templates.resolver import resolve_template

        template = MagicMock()
        mock_db.execute.return_value = make_execute_result(scalar=template)

        await resolve_template(VALID_UUID, OWNER, mock_db)

        # Only one execute call: the UUID query
        mock_db.execute.assert_called_once()

    async def test_uuid_finds_global_template(self, mock_db):
        """UUID lookup is owner-agnostic — returns a global (owner=NULL) template directly."""
        from app.templates.resolver import resolve_template

        global_template = MagicMock()
        global_template.owner = None
        mock_db.execute.return_value = make_execute_result(scalar=global_template)

        result = await resolve_template(VALID_UUID, OWNER, mock_db)

        assert result is global_template
        # UUID path short-circuits — no name or global fallback queries
        mock_db.execute.assert_called_once()

    async def test_owner_template_takes_priority_over_global(self, mock_db):
        """Owner-scoped name hit → global fallback is never queried."""
        from app.templates.resolver import resolve_template

        owner_template = MagicMock()
        owner_template.owner = OWNER
        mock_db.execute.return_value = make_execute_result(scalar=owner_template)

        result = await resolve_template("shared-name", OWNER, mock_db)

        assert result is owner_template
        # Only the owner-scoped name query; global fallback must not fire
        mock_db.execute.assert_called_once()

    async def test_global_fallback_skipped_when_uuid_found(self, mock_db):
        """UUID hit for a non-global template → no fallback queries at all."""
        from app.templates.resolver import resolve_template

        owned_template = MagicMock()
        owned_template.owner = OWNER
        mock_db.execute.return_value = make_execute_result(scalar=owned_template)

        result = await resolve_template(VALID_UUID, OWNER, mock_db)

        assert result is owned_template
        mock_db.execute.assert_called_once()

    async def test_uuid_miss_global_fallback_finds_by_name(self, mock_db):
        """UUID miss → owner name miss → global fallback hit."""
        from app.templates.resolver import resolve_template

        global_template = MagicMock()
        global_template.owner = None
        mock_db.execute.side_effect = [
            make_execute_result(scalar=None),            # UUID lookup: miss
            make_execute_result(scalar=None),            # name+owner lookup: miss
            make_execute_result(scalar=global_template), # global fallback: hit
        ]

        result = await resolve_template(VALID_UUID, OWNER, mock_db)

        assert result is global_template
        assert mock_db.execute.call_count == 3

    async def test_global_fallback_not_reached_when_owner_name_found(self, mock_db):
        """Owner name lookup success → exactly one query, no global fallback."""
        from app.templates.resolver import resolve_template

        owner_template = MagicMock()
        mock_db.execute.return_value = make_execute_result(scalar=owner_template)

        result = await resolve_template("my-prompt", OWNER, mock_db)

        assert result is owner_template
        mock_db.execute.assert_called_once()

    async def test_error_message_includes_template_identifier(self, mock_db):
        """NotFoundError message contains the requested name/id for debuggability."""
        from app.templates.resolver import resolve_template
        from app.exceptions import NotFoundError

        mock_db.execute.side_effect = [
            make_execute_result(scalar=None),
            make_execute_result(scalar=None),
        ]

        with pytest.raises(NotFoundError, match="ghost-template"):
            await resolve_template("ghost-template", OWNER, mock_db)
