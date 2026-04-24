"""
Auto Router classifier — builds the routing prompt and calls the classifier LLM.

call_classifier() returns a (content, failure_reason, usage) triple:
  ("model-id", "", usage_dict)      — success; content still needs validation
  (None, "classifier_timeout", None) — asyncio.wait_for timed out
  (None, "classifier_error", None)   — any other exception from the adapter

usage_dict shape (mirrors the adapter response.usage field, plus metadata):
  {
    "model_id":           str,           # gateway model ID (e.g. "openai/gpt-4o-mini")
    "prompt_tokens":      int | None,
    "completion_tokens":  int | None,
    "cost":               float | None,  # USD, as reported by the upstream
  }
"""

from __future__ import annotations

import asyncio
import time

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auto_router.registry import CandidateModel
from app.config import settings
from app.schemas.chat import ChatCompletionRequest, Message

logger = structlog.get_logger()

_SYSTEM_PROMPT = (
    "You are a model routing assistant. Select the single most appropriate model "
    "for the user's request. Respond with ONE model ID and nothing else — no quotes, "
    "no punctuation, no explanation. The ID must come verbatim from the provided list."
)


def _build_user_message(candidates: list[CandidateModel], user_content: str) -> str:
    lines = ["Available models:"]
    for c in candidates:
        cap = c.description if c.description else "General purpose"
        lines.append(f"- ID: {c.model_id}  Name: {c.name}  Capabilities: {cap}")
    lines += [
        "",
        "User request:",
        '"""',
        user_content[:2000],
        '"""',
        "",
        "Respond with the ID of the most suitable model.",
    ]
    return "\n".join(lines)


async def call_classifier(
    candidates: list[CandidateModel],
    user_content: str,
    *,
    db: AsyncSession,
    classifier_model_id: str | None = None,
    request_id: str = "",
    owner: str,
) -> tuple[str | None, str, dict | None]:
    """
    Call the classifier LLM and return (raw_content, failure_reason, usage).

    failure_reason is "" on success, "classifier_timeout" on timeout, or
    "classifier_error" on any other exception. usage is None on failure.

    classifier_model_id overrides settings.auto_router_classifier_model_id,
    allowing callers to retry with a different model (e.g. the fallback classifier).
    The model is resolved via resolve_routing() to support any provider.
    """
    from app.providers.key_resolver import resolve_upstream_key
    from app.providers.registry import get_adapter, resolve_routing

    model_id = classifier_model_id or settings.auto_router_classifier_model_id

    # Resolve the classifier model to its provider and provider-specific model ID
    provider, provider_model_id, _ = await resolve_routing(model_id, db)

    # Get the upstream API key for that provider
    upstream_key = await resolve_upstream_key(owner=owner, provider=provider, db=db)

    # Get the appropriate adapter for the provider
    adapter = get_adapter(provider)

    classifier_request = ChatCompletionRequest(
        model=model_id,
        messages=[
            Message(role="system", content=_SYSTEM_PROMPT),
            Message(role="user", content=_build_user_message(candidates, user_content)),
        ],
        temperature=settings.auto_router_classifier_temperature,
        max_tokens=settings.auto_router_classifier_max_tokens,
        stream=False,
    )

    timeout_s = settings.auto_router_classifier_timeout_ms / 1000.0
    start = time.monotonic()

    try:
        response = await asyncio.wait_for(
            adapter.chat_completion(
                classifier_request,
                api_key=upstream_key,
                owner=None,
                provider_model_id=provider_model_id,
            ),
            timeout=timeout_s,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        choices = response.get("choices") or []
        if not choices:
            return None, "classifier_error", None

        content = (choices[0].get("message") or {}).get("content") or ""

        raw_usage = response.get("usage") or {}
        usage: dict | None = {
            "model_id": model_id,
            "prompt_tokens": raw_usage.get("prompt_tokens"),
            "completion_tokens": raw_usage.get("completion_tokens"),
        }

        logger.info(
            "classifier_call_complete",
            request_id=request_id,
            classifier_model=model_id,
            provider=provider,
            elapsed_ms=elapsed_ms,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
        )
        return content, "", usage

    except TimeoutError:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "classifier_timeout",
            request_id=request_id,
            classifier_model=model_id,
            provider=provider,
            timeout_ms=settings.auto_router_classifier_timeout_ms,
            elapsed_ms=elapsed_ms,
        )
        return None, "classifier_timeout", None

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "classifier_error",
            request_id=request_id,
            classifier_model=model_id,
            provider=provider,
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )
        return None, "classifier_error", None


def parse_classifier_response(raw: str | None, valid_ids: set[str]) -> str | None:
    """
    Validate the classifier's raw text response.

    Steps:
      1. None or empty → None
      2. Strip whitespace, take first line
      3. Check non-empty and exact membership in valid_ids
      4. Return the validated model ID, or None on any failure
    """
    if not raw:
        return None

    stripped = raw.strip()
    if not stripped:
        return None

    first_line = stripped.splitlines()[0].strip()
    if not first_line:
        return None

    if first_line not in valid_ids:
        logger.warning(
            "classifier_invalid_response",
            raw_response=raw[:100],
            first_line=first_line,
        )
        return None

    return first_line
