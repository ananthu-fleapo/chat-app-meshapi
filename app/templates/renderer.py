"""
Template renderer — variable substitution + message assembly.

The renderer is a pure function (no I/O). It takes a Template ORM instance
and a variables dict, performs {{slot}} substitution, and returns the
assembled message list that gets prepended to body.messages.

Substitution rules
------------------
- Delimiters:  {{ variable_name }}  (whitespace inside braces is trimmed)
- Variable names must match \\w+ (letters, digits, underscores)
- A referenced variable that is missing in the supplied dict raises
  UnprocessableEntityError immediately — rendering is aborted.
- Extra keys in the variables dict are silently ignored.
- Substitution is applied to: template.system and each message's content
  string. Multi-part content (list[ContentPart]) is not substituted —
  pass variables inside text parts manually for now.

Example
-------
template.system = "You are a {{tone}} assistant who speaks {{language}}."
variables       = {"tone": "friendly", "language": "Spanish"}
result system   = "You are a friendly assistant who speaks Spanish."
"""

import re

import structlog

from app.db.models import Template
from app.exceptions import UnprocessableEntityError

logger = structlog.get_logger()

# Matches {{ var_name }} with optional surrounding whitespace inside braces.
_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _render_text(text: str, variables: dict[str, str], template_name: str) -> str:
    """Replace all {{slots}} in text. Raises 422 on first missing variable."""

    def _replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in variables:
            raise UnprocessableEntityError(
                f"Template '{template_name}' requires variable '{{{{{key}}}}}' "
                f"but it was not provided in body.variables."
            )
        return str(variables[key])

    return _VAR_RE.sub(_replace, text)


def render_template(
    template: Template,
    variables: dict[str, str] | None,
) -> list[dict]:
    """
    Render a template into a list of messages dicts.

    Returns the rendered base messages (system + template.messages).
    The caller is responsible for appending body.messages afterwards:

        rendered = render_template(template, body.variables)
        final_messages = rendered + [m.model_dump() for m in body.messages]

    Parameters
    ----------
    template    The Template ORM instance (not session-attached is fine).
    variables   Values for {{slot}} placeholders. None treated as {}.

    Raises
    ------
    UnprocessableEntityError  If a referenced {{slot}} is not in variables.
    """
    vars_: dict[str, str] = variables or {}
    result: list[dict] = []

    # ── System prompt ─────────────────────────────────────────────────────────
    if template.system:
        rendered_system = _render_text(template.system, vars_, template.name)
        result.append({"role": "system", "content": rendered_system})

    # ── Base message turns ────────────────────────────────────────────────────
    for msg in template.messages or []:
        content = msg.get("content", "")
        if isinstance(content, str):
            content = _render_text(content, vars_, template.name)
        # Non-string content (multipart) passes through unchanged.
        result.append({"role": msg["role"], "content": content})

    logger.debug(
        "template_rendered",
        template_id=str(template.id),
        template_name=template.name,
        base_message_count=len(result),
        variable_count=len(vars_),
    )
    return result
