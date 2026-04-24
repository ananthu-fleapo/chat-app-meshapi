"""
Request schema for the Responses API endpoint (POST /v1/responses).

The Responses API is OpenRouter's higher-level endpoint for reasoning models.
Key differences from chat/completions:
- `input` (str or messages list) instead of `messages`
- `max_output_tokens` instead of `max_tokens`
- First-class `reasoning` field ({"effort": "minimal|low|medium|high"})
- `plugins` for web search (deprecated; prefer tools with "openrouter:web_search")
- `response_format` for structured outputs

All inference params are Optional with None defaults — the config resolver
fills them in from key.default_params using the same layering pattern as
chat/completions.
"""

from pydantic import BaseModel, Field

from app.schemas.chat import Tool

# Fields RouterV consumes internally; stripped before forwarding upstream.
RESPONSES_ONLY_FIELDS: set[str] = {"template", "variables", "session_id"}


class ResponsesRequest(BaseModel):
    # model is Optional — resolve_responses_config() fills it from key.default_model.
    model: str | None = None

    # Required — string query or structured messages list.
    # When a list, objects follow the same role/content structure as chat/completions.
    input: str | list

    # ── RouterV extensions (stripped before upstream forwarding) ──────────────
    template: str | None = None  # reserved for future template support
    variables: dict[str, str] | None = None  # {{slot}} → value
    session_id: str | None = None  # groups related requests

    # ── Standard inference params (all Optional for config resolver layering) ─
    stream: bool = False
    max_output_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    seed: int | None = None

    # ── Responses API-specific fields ─────────────────────────────────────────
    # Enables chain-of-thought reasoning; effort controls depth vs. token cost.
    reasoning: dict | None = None  # {"effort": "minimal|low|medium|high"}
    tools: list[Tool] | None = None  # function tool definitions (OpenAI format)
    tool_choice: str | dict | None = None  # "auto" | "none" | specific tool
    response_format: dict | None = None  # {"type": "json_object"} or json_schema

    # Web search via plugins (deprecated by OpenRouter — prefer tools with
    # "openrouter:web_search" server tool, but still accepted for compatibility).
    plugins: list | None = None

    # ── OpenAI-compatible tracking field ──────────────────────────────────────
    user: str | None = Field(default=None, max_length=256)
