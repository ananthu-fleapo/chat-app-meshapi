"""
Model Health Check — POST /v1/model-health/run

Tests every enabled model with a minimal prompt and reports pass/fail results
to Slack. Intended to be triggered by Cloud Scheduler every 6 hours.

Auth: WEBHOOK_API_KEY bearer token (same as /v1/fx-rates/refresh).

Cloud Scheduler config:
    Schedule:  0 */6 * * *
    URL:       POST https://<routersvc-url>/v1/model-health/run
    Header:    Authorization: Bearer <WEBHOOK_API_KEY>
"""

from __future__ import annotations

import asyncio
import contextvars
import time
from datetime import UTC, datetime

import structlog
import structlog.contextvars
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sqlalchemy import select

from app.auth.dependencies import verify_webhook_key
from app.db.engine import get_session_factory
from app.db.models import Model
from app.notifications.slack import send_slack_alert
from app.providers.key_resolver import resolve_upstream_key
from app.providers.registry import get_adapter, resolve_routing
from app.schemas.chat import ChatCompletionRequest, Message

logger = structlog.get_logger()
router = APIRouter(tags=["model-health"])

_CONCURRENCY = 5
_TIMEOUT_S = 60.0
_TEST_MESSAGES = [Message(role="user", content="Say hi")]
_MAX_TOKENS = 1024


# ── Response schema ───────────────────────────────────────────────────────────

class ModelHealthResult(BaseModel):
    model_id: str
    status: str          # "pass" | "fail" | "timeout" | "degraded"
    latency_ms: int
    error: str | None = None
    provider: str | None = None
    upstream_status: int | None = None


class ModelHealthResponse(BaseModel):
    total: int
    passed: int
    failed: int
    pass_rate: str
    avg_latency_ms: int
    results: list[ModelHealthResult]


# ── Internals ─────────────────────────────────────────────────────────────────

async def _test_model(model_id: str) -> ModelHealthResult:
    """Test a single model with a minimal prompt. Never raises.

    Opens its own DB session for provider routing so it is safe to run
    concurrently with other _test_model calls via asyncio.gather.

    Binds per-model structlog context vars (model_id, provider,
    provider_model_id) so every log line carries them automatically.
    The caller schedules this via asyncio.create_task(context=...) so
    each task gets an isolated copy of the context, preventing cross-task
    bleed when running concurrently.
    """
    structlog.contextvars.bind_contextvars(model_id=model_id)

    start = time.monotonic()
    provider: str | None = None
    provider_model_id: str | None = None
    request: ChatCompletionRequest | None = None
    try:
        async with get_session_factory()() as session:
            provider, provider_model_id = await resolve_routing(model_id, session)
            # Resolve the system-default upstream key (db=None skips per-owner lookup)
            api_key = await resolve_upstream_key(owner="health-check", provider=provider, db=None)
        structlog.contextvars.bind_contextvars(provider=provider, provider_model_id=provider_model_id)
        adapter = get_adapter(provider)
        request = ChatCompletionRequest(
            model=model_id,
            messages=_TEST_MESSAGES,
            max_tokens=_MAX_TOKENS,
            stream=False,
        )
        await asyncio.wait_for(
            adapter.chat_completion(request, api_key=api_key, provider_model_id=provider_model_id),
            timeout=_TIMEOUT_S,
        )
        return ModelHealthResult(
            model_id=model_id,
            status="pass",
            latency_ms=int((time.monotonic() - start) * 1000),
            provider=provider,
        )
    except asyncio.TimeoutError:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "model_health_timeout",
            timeout_s=_TIMEOUT_S,
            latency_ms=latency_ms,
            request_messages=[m.model_dump() for m in _TEST_MESSAGES],
            request_max_tokens=_MAX_TOKENS,
            request_stream=False,
        )
        return ModelHealthResult(model_id=model_id, status="timeout", latency_ms=latency_ms, provider=provider)
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        cause = getattr(exc, "__cause__", None)
        upstream_status = getattr(getattr(cause, "response", None), "status_code", None)
        upstream_body = getattr(getattr(cause, "response", None), "text", None)
        if upstream_body:
            upstream_body = upstream_body[:300]
        # 429 = model exists and works, provider is just rate-limiting the health check.
        # Report as "degraded" so it doesn't page alongside genuine failures.
        status = "degraded" if upstream_status == 429 else "fail"
        log_fn = logger.warning if status == "degraded" else logger.exception
        log_fn(
            "model_health_fail",
            latency_ms=latency_ms,
            exc_type=type(exc).__name__,
            error=str(exc),
            upstream_status=upstream_status,
            upstream_body=upstream_body,
            request_messages=[m.model_dump() for m in _TEST_MESSAGES],
            request_max_tokens=_MAX_TOKENS,
            request_stream=False,
            request_schema=request.model_dump() if request else None,
        )
        return ModelHealthResult(
            model_id=model_id,
            status=status,
            latency_ms=latency_ms,
            error=str(exc),
            provider=provider,
            upstream_status=upstream_status,
        )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/v1/model-health/run", response_model=ModelHealthResponse)
async def run_model_health(
    _: None = Depends(verify_webhook_key),
) -> ModelHealthResponse:
    """
    Test all enabled models and send results to Slack.
    Triggered by Cloud Scheduler every 6 hours.
    """
    logger.info("model_health_check_started")

    # Query models table directly — all is_enabled rows.
    async with get_session_factory()() as session:
        result = await session.execute(
            select(Model.model_id).where(Model.is_enabled.is_(True)).order_by(Model.model_id)
        )
        model_ids = list(result.scalars().all())
    logger.info("model_health_models_fetched", count=len(model_ids))

    # Batched concurrency — 5 models tested in parallel per batch
    results: list[ModelHealthResult] = []
    queue = list(model_ids)
    while queue:
        batch = queue[:_CONCURRENCY]
        queue = queue[_CONCURRENCY:]
        batch_results = await asyncio.gather(*[
            asyncio.create_task(_test_model(mid), context=contextvars.copy_context())
            for mid in batch
        ])
        results.extend(batch_results)

    passed = [r for r in results if r.status == "pass"]
    timeouts = [r for r in results if r.status == "timeout"]
    pure_fails = [r for r in results if r.status == "fail"]
    degraded = [r for r in results if r.status == "degraded"]
    # "not working" = genuine failures + timeouts; degraded (429) excluded
    not_working = pure_fails + timeouts
    total = len(results)
    pass_rate = f"{(len(passed) / total * 100):.1f}%" if total else "0.0%"
    avg_latency = (
        int(sum(r.latency_ms for r in passed) / len(passed)) if passed else 0
    )

    logger.info(
        "model_health_check_completed",
        total=total,
        passed=len(passed),
        degraded=len(degraded),
        failed=len(pure_fails),
        timeouts=len(timeouts),
        avg_latency_ms=avg_latency,
    )

    # Build Slack message — group by status for clarity
    non_passing = not_working + degraded
    failed_message: str | None = None
    if non_passing:
        lines = []
        for r in non_passing:
            detail = ""
            if r.provider:
                detail = f" {r.provider}"
                if r.upstream_status:
                    detail += f" → HTTP {r.upstream_status}"
            if r.status == "timeout":
                detail += f" ({_TIMEOUT_S}s timeout)"
            err_str = f": {r.error}" if r.error and r.status not in ("timeout", "degraded") else ""
            lines.append(f"• `{r.model_id}` [{r.status}]{detail}{err_str}")
        failed_message = "\n".join(lines)

    await send_slack_alert(
        title=f"Model Health Check — {len(passed)}/{total} passed",
        fields=[
            {"label": "Timestamp", "value": datetime.now(UTC).isoformat()},
            {"label": "Pass Rate", "value": pass_rate},
            {"label": "Avg Latency (passing)", "value": f"{avg_latency}ms"},
            {"label": "Failures", "value": str(len(pure_fails))},
            {"label": "Timeouts", "value": str(len(timeouts))},
            {"label": "Degraded (rate-limited)", "value": str(len(degraded))},
        ],
        message=failed_message,
        notify_here=bool(not_working),  # only page for genuine failures/timeouts, not 429s
    )

    return ModelHealthResponse(
        total=total,
        passed=len(passed),
        failed=len(not_working),
        pass_rate=pass_rate,
        avg_latency_ms=avg_latency,
        results=results,
    )
