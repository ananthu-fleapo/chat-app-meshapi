"""
Config resolver — merges three config layers into the final request.

Priority order (highest → lowest)
----------------------------------
1. Request body   — explicit caller choices, always respected.
2. Key defaults   — key.default_model + key.default_params.
3. Template       — template.model + template.params (lowest, "suggestions").

Messages
--------
If a template was resolved, its rendered messages are PREPENDED before
body.messages:

    final = [system_from_template] + [template turns] + [body.messages]

This lets templates establish a persona / context while the caller's
conversation continues naturally after the base turns.

If no template: body.messages passed through unchanged.

Note: tools / tool_choice / stream are never pulled from defaults —
they are structural choices, not tuning params.
"""

from app.db.models import ApiKey, Template
from app.exceptions import UnprocessableEntityError
from app.schemas.chat import ChatCompletionRequest, Message

_MERGEABLE_PARAMS: tuple[str, ...] = (
    "temperature",
    "max_tokens",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
    "stop",
    "seed",
)


def resolve_config(
    body: ChatCompletionRequest,
    key: ApiKey,
    template: Template | None = None,
    rendered_messages: list[dict] | None = None,
) -> ChatCompletionRequest:
    """
    Merge all config layers and return the finalised ChatCompletionRequest.

    Parameters
    ----------
    body               Original request from the caller.
    key                Authenticated ApiKey (layer-2 defaults).
    template           Resolved Template if body.template was set, else None.
    rendered_messages  Pre-rendered base messages from render_template().
                       Prepended before body.messages when provided.

    Returns
    -------
    A new ChatCompletionRequest ready for the upstream provider.
    RouterV-only fields (template, variables, session_id) are carried through
    — they are stripped from the upstream payload in _build_payload().
    """
    key_defaults: dict = key.default_params or {}
    tmpl_defaults: dict = (template.params or {}) if template else {}
    data = body.model_dump()

    # ── Model: body → key → template → error ─────────────────────────────────
    if data["model"] is None:
        data["model"] = key.default_model
    if data["model"] is None and template is not None:
        data["model"] = template.model
    if data["model"] is None:
        raise UnprocessableEntityError(
            "model is required. Set it in the request, configure default_model "
            "on your API key, or specify a model in the template."
        )

    # ── Inference params: body → key → template ───────────────────────────────
    for param in _MERGEABLE_PARAMS:
        if data.get(param) is None:
            if param in key_defaults:
                data[param] = key_defaults[param]
            elif param in tmpl_defaults:
                data[param] = tmpl_defaults[param]

    # ── Messages: [template base] + [body.messages] ───────────────────────────
    if rendered_messages:
        base = [Message(**m) for m in rendered_messages]
        data["messages"] = base + (data.get("messages") or [])

    return ChatCompletionRequest(**data)
