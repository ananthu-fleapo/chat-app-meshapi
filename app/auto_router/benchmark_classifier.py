"""
Benchmark-mode classifier — classifies a user request into a CATEGORY and MODE.

call_benchmark_classifier() returns a (raw_content, failure_reason, usage) triple
with the same contract as call_classifier() in classifier.py, so service.py can
handle both paths uniformly.

parse_benchmark_response() parses the raw "CATEGORY,MODE" string into a validated
(category, mode) pair ready for resolve_from_benchmark_category().
"""

from __future__ import annotations

import asyncio
import time

import structlog

from app.auto_router.benchmarks import SUPERMODE_CATEGORIES
from app.config import settings
from app.schemas.chat import ChatCompletionRequest, Message

logger = structlog.get_logger()

_BENCHMARK_SYSTEM_PROMPT = """\
## Input
- CATEGORIES: allowed category names (must match exactly).
- USER_PROMPT: the user request.

## Task
1) Select the single best category from CATEGORIES that matches the primary goal of USER_PROMPT.
2) Choose MODE [premium or standard]: premium if the user request requires deep analysis, \
thinking, etc. Otherwise choose standard.

## Rules
- CATEGORY must be exactly as written in CATEGORIES (case/punctuation).
- If multiple fit, pick the best primary match.
- If USER_PROMPT mentions any form of document generation (pdf, pptx, excel, docx), \
CATEGORY MUST BE: `File generation - pdf, docx, pptx, excel` and MODE MUST BE: `premium`.

## Output (hard constraint)
Return exactly: CATEGORY,MODE  (no extra text, no quotes, no JSON, no newlines).\
"""

_CATEGORIES_BLOCK = "Categories:\n" + "\n".join(f"- {c}" for c in SUPERMODE_CATEGORIES)


def _build_benchmark_user_message(user_content: str) -> str:
    return "\n".join([
        _CATEGORIES_BLOCK,
        "",
        "User request:",
        '"""',
        user_content[:2000],
        '"""',
    ])


async def call_benchmark_classifier(
    user_content: str,
    *,
    db,
    classifier_model_id: str | None = None,
    request_id: str = "",
    owner: str,
) -> tuple[str | None, str, dict | None]:
    """
    Call the benchmark classifier LLM and return (raw_content, failure_reason, usage).

    Same triple contract as call_classifier():
      (raw_str, "", usage_dict)           — success
      (None, "classifier_timeout", None)  — timed out
      (None, "classifier_error", None)    — any other exception
    """
    from app.providers.key_resolver import resolve_upstream_key
    from app.providers.registry import get_adapter, resolve_routing

    model_id = classifier_model_id or settings.auto_router_classifier_model_id

    provider, provider_model_id, _ = await resolve_routing(model_id, db)
    upstream_key = await resolve_upstream_key(owner=owner, provider=provider, db=db)
    adapter = get_adapter(provider)

    classifier_request = ChatCompletionRequest(
        model=model_id,
        messages=[
            Message(role="system", content=_BENCHMARK_SYSTEM_PROMPT),
            Message(role="user", content=_build_benchmark_user_message(user_content)),
        ],
        temperature=settings.auto_router_classifier_temperature,
        max_tokens=64,
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
            "provider": provider,
            "prompt_tokens": raw_usage.get("prompt_tokens"),
            "completion_tokens": raw_usage.get("completion_tokens"),
            "cost": raw_usage.get("cost"),
        }

        logger.info(
            "benchmark_classifier_call_complete",
            request_id=request_id,
            classifier_model=model_id,
            provider=provider,
            elapsed_ms=elapsed_ms,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            cost_usd=usage["cost"],
        )
        return content, "", usage

    except asyncio.TimeoutError:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "benchmark_classifier_timeout",
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
            "benchmark_classifier_error",
            request_id=request_id,
            classifier_model=model_id,
            provider=provider,
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )
        return None, "classifier_error", None


_VALID_MODES = {"premium", "standard"}
_CATEGORIES_SET = set(SUPERMODE_CATEGORIES)


def parse_benchmark_response(raw: str | None) -> tuple[str | None, str]:
    """
    Parse the classifier's "CATEGORY,MODE" response.

    Returns (category, mode) on success or (None, "") on failure.
    Splits on the last comma so categories that themselves contain commas
    (none currently, but safe) are handled correctly.
    Mode defaults to "premium" when absent or unrecognised.
    """
    if not raw:
        return None, ""

    stripped = raw.strip().splitlines()[0].strip()
    if not stripped:
        return None, ""

    # Split on last comma to isolate mode.
    last_comma = stripped.rfind(",")
    if last_comma == -1:
        category = stripped
        mode = "premium"
    else:
        category = stripped[:last_comma].strip()
        mode_raw = stripped[last_comma + 1:].strip().lower()
        mode = mode_raw if mode_raw in _VALID_MODES else "premium"

    if category not in _CATEGORIES_SET:
        logger.warning(
            "benchmark_classifier_invalid_response",
            raw_response=raw[:120],
            parsed_category=category,
        )
        return None, ""

    return category, mode
