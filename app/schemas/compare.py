"""
Request / response schemas for POST /v1/chat/compare.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.chat import Message


class ModelOverride(BaseModel):
    """Per-model parameter overrides applied on top of the request-level defaults."""

    model: str
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    system_prompt: str | None = None


class CompareRequest(BaseModel):
    # ── Required ──────────────────────────────────────────────────────────────
    models: list[str] = Field(..., min_length=1, max_length=10)
    messages: list[Message]

    # ── Per-model overrides ───────────────────────────────────────────────────
    model_overrides: list[ModelOverride] | None = None

    # ── Comparison LLM config ─────────────────────────────────────────────────
    comparison_model: str | None = None
    comparison_instructions: str | None = None

    # ── Standard inference params forwarded to ALL fan-out models ────────────
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = False

    # ── RouterV extensions ────────────────────────────────────────────────────
    template: str | None = None
    variables: dict[str, str] | None = None

    # ── Comparison control ────────────────────────────────────────────────────
    skip_comparison: bool = False


class TokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ModelCompareResult(BaseModel):
    model: str
    response_body: dict | None = None
    content: str | None = None
    latency_ms: int
    error: str | None = None
    error_code: str | None = None
    usage: TokenUsage | None = None
    request_id: str


class CompareResponse(BaseModel):
    comparison_id: str
    object: Literal["compare.completion"] = "compare.completion"
    created: int
    models: list[str]
    results: list[ModelCompareResult]
    comparison: str | None = None
    comparison_model: str | None = None
    comparison_usage: TokenUsage | None = None
    comparison_fallback_used: bool = False
    total_latency_ms: int
    partial: bool = False
    skip_comparison: bool = False
