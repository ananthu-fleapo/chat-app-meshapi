"""
Unit tests for app/templates/renderer.py

Covers:
  render_template — variable substitution in system prompt and messages,
                    missing variable error, extra variables ignored,
                    no-system / no-messages edge cases, multipart content pass-through
  _render_text    — whitespace-tolerant {{ name }} syntax
"""

from unittest.mock import MagicMock

import pytest

from app.exceptions import UnprocessableEntityError
from app.templates.renderer import render_template


def _make_template(system=None, messages=None, name="test-tmpl"):
    """Build a minimal Template-like object (no DB session required)."""
    t = MagicMock()
    t.id = "00000000-0000-0000-0000-000000000001"
    t.name = name
    t.system = system
    t.messages = messages or []
    return t


class TestRenderTemplate:

    def test_system_prompt_substituted(self):
        """{{slot}} in system is replaced with the supplied value."""
        tmpl = _make_template(system="You are a {{tone}} assistant.")
        result = render_template(tmpl, {"tone": "friendly"})
        assert result == [{"role": "system", "content": "You are a friendly assistant."}]

    def test_message_content_substituted(self):
        """{{slot}} inside a message turn is also substituted."""
        tmpl = _make_template(messages=[{"role": "user", "content": "Hello {{name}}!"}])
        result = render_template(tmpl, {"name": "Alice"})
        assert result == [{"role": "user", "content": "Hello Alice!"}]

    def test_system_and_messages_both_substituted(self):
        """Both system and message turns are rendered."""
        tmpl = _make_template(
            system="Context: {{ctx}}",
            messages=[{"role": "user", "content": "Q: {{q}}"}],
        )
        result = render_template(tmpl, {"ctx": "finance", "q": "What is EBITDA?"})
        assert result[0] == {"role": "system", "content": "Context: finance"}
        assert result[1] == {"role": "user", "content": "Q: What is EBITDA?"}

    def test_missing_variable_raises_422(self):
        """A referenced {{slot}} not in variables dict raises UnprocessableEntityError."""
        tmpl = _make_template(system="Hello {{missing_var}}.")
        with pytest.raises(UnprocessableEntityError):
            render_template(tmpl, {})

    def test_missing_variable_error_mentions_slot_name(self):
        """Error message should name the missing variable so the caller can fix it."""
        tmpl = _make_template(system="Hello {{secret_var}}.")
        with pytest.raises(UnprocessableEntityError) as exc_info:
            render_template(tmpl, {})
        assert "secret_var" in str(exc_info.value.message)

    def test_extra_variables_ignored(self):
        """Variables provided but not referenced in the template are silently ignored."""
        tmpl = _make_template(system="Hello {{name}}.")
        # "unused_key" is extra
        result = render_template(tmpl, {"name": "Bob", "unused_key": "ignored"})
        assert result == [{"role": "system", "content": "Hello Bob."}]

    def test_no_system_prompt_no_system_message(self):
        """Template without a system prompt produces no system message in output."""
        tmpl = _make_template(
            system=None,
            messages=[{"role": "user", "content": "Hi"}],
        )
        result = render_template(tmpl, {})
        assert all(m["role"] != "system" for m in result)
        assert len(result) == 1

    def test_no_messages_only_system(self):
        """Template with system only returns just the system message."""
        tmpl = _make_template(system="You are helpful.", messages=[])
        result = render_template(tmpl, {})
        assert result == [{"role": "system", "content": "You are helpful."}]

    def test_variables_none_treated_as_empty_dict(self):
        """Passing variables=None should not crash when there are no slots."""
        tmpl = _make_template(system="No slots here.", messages=[])
        result = render_template(tmpl, None)
        assert result == [{"role": "system", "content": "No slots here."}]

    def test_multipart_content_passes_through_unchanged(self):
        """Non-string (list) content is not substituted — passed through as-is."""
        multipart = [{"type": "text", "text": "image desc"}, {"type": "image_url"}]
        tmpl = _make_template(messages=[{"role": "user", "content": multipart}])
        result = render_template(tmpl, {})
        assert result[0]["content"] == multipart

    def test_whitespace_inside_braces_accepted(self):
        """{{ name }} (with spaces) should substitute the same as {{name}}."""
        tmpl = _make_template(system="Hello {{ name }}.")
        result = render_template(tmpl, {"name": "Carol"})
        assert result[0]["content"] == "Hello Carol."

    def test_multiple_slots_in_one_string(self):
        """Multiple slots in a single string are all substituted."""
        tmpl = _make_template(system="{{greeting}}, {{name}}! You speak {{lang}}.")
        result = render_template(tmpl, {"greeting": "Hi", "name": "Dan", "lang": "Python"})
        assert result[0]["content"] == "Hi, Dan! You speak Python."

    def test_empty_template_returns_empty_list(self):
        """Template with no system and no messages → empty list."""
        tmpl = _make_template(system=None, messages=[])
        result = render_template(tmpl, {})
        assert result == []

    def test_output_ordering_system_first(self):
        """System message must always be first in the output list."""
        tmpl = _make_template(
            system="System context.",
            messages=[{"role": "user", "content": "Hello"}],
        )
        result = render_template(tmpl, {})
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
