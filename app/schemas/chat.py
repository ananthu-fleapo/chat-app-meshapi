"""
Request / response schemas for the inference endpoints.

Design notes:
- All inference params (temperature, max_tokens, etc.) are Optional[...] with
  None defaults. Phase 2's config resolver fills them in from key defaults and
  template defaults without field collisions.
- `model` is Optional for the same reason — a key may have a default_model.
  Phase 1 raises 422 if it's still None after the (absent) resolver step.
- RouterV-only fields (template, variables, session_id) are declared here but
  stripped from the payload before forwarding to the upstream provider.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Fields that RouterV consumes internally and must never be forwarded upstream.
ROUTERV_ONLY_FIELDS: set[str] = {"template", "variables", "session_id"}


# ── Sub-models ────────────────────────────────────────────────────────────────


class ImageUrl(BaseModel):
    url: str
    detail: Literal["auto", "low", "high"] = "auto"


class ContentPart(BaseModel):
    type: Literal["text", "image_url"]
    text: str | None = None
    image_url: ImageUrl | None = None


class ToolFunction(BaseModel):
    name: str
    description: str | None = None
    parameters: dict | None = None


class Tool(BaseModel):
    type: Literal["function"] = "function"
    function: ToolFunction


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: dict  # {name, arguments}


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[ContentPart] | None = None
    name: str | None = None
    tool_call_id: str | None = None  # present when role=="tool"
    tool_calls: list[ToolCall] | None = None  # present when role=="assistant" with tool use


# ── Request ───────────────────────────────────────────────────────────────────


class ChatCompletionRequest(BaseModel):
    model: str | None = None

    messages: list[Message]

    # ── RouterV extensions (stripped before upstream forwarding) ──────────────
    template: str | None = None  # template name/id
    variables: dict[str, str] | None = None  # {{slot}} → value
    session_id: str | None = None  # groups related requests

    # ── Standard inference params (all Optional for config resolver layering) ─
    stream: bool = False
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    stop: str | list[str] | None = None
    seed: int | None = None
    tools: list[Tool] | None = None
    tool_choice: str | dict | None = None

    # ── OpenRouter-specific extensions ────────────────────────────────────────
    # `transforms` — e.g. ["middle-out"] for context compression
    transforms: list[str] | None = None
    # `models` — ordered fallback list if primary model is unavailable
    models: list[str] | None = None

    # ── OpenAI-compatible tracking field ──────────────────────────────────────
    # Clients (e.g. OpenAI SDK) may send this for abuse-detection tracking.
    # Enforced to 256 chars here so oversized values 422 at our layer, not 400
    # from OpenRouter. Our code sets a default via setdefault if not provided.
    user: str | None = Field(default=None, max_length=256)


# ── Response ──────────────────────────────────────────────────────────────────


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Choice(BaseModel):
    index: int
    message: Message | None = None
    delta: dict | None = None  # populated in streaming chunks
    finish_reason: str | None = None
    logprobs: dict | None = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[Choice]
    usage: UsageInfo | None = None
    system_fingerprint: str | None = None
