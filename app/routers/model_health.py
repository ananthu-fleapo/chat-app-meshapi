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
import time
from datetime import UTC, datetime

import structlog
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
_TIMEOUT_S = 20.0
_TEST_MESSAGES = [Message(role="user", content="Say hi")]
_MAX_TOKENS = 10


# ── Response schema ───────────────────────────────────────────────────────────

class ModelHealthResult(BaseModel):
    model_id: str
    status: str          # "pass" | "fail" | "timeout"
    latency_ms: int
    error: str | None = None


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
    """
    start = time.monotonic()
    try:
        async with get_session_factory()() as session:
            provider, provider_model_id = await resolve_routing(model_id, session)
            # Resolve the system-default upstream key (db=None skips per-owner lookup)
            api_key = await resolve_upstream_key(owner="health-check", provider=provider, db=None)
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
        )
    except asyncio.TimeoutError:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning("model_health_timeout", model_id=model_id, latency_ms=latency_ms)
        return ModelHealthResult(model_id=model_id, status="timeout", latency_ms=latency_ms)
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.exception(
        "model_health_fail",
        model_id=model_id,
        latency_ms=latency_ms
       )
        return ModelHealthResult(model_id=model_id, status="fail", latency_ms=latency_ms, error=str(exc))


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
        batch_results = await asyncio.gather(*[_test_model(mid) for mid in batch])
        results.extend(batch_results)

    passed = [r for r in results if r.status == "pass"]
    failed = [r for r in results if r.status != "pass"]
    total = len(results)
    pass_rate = f"{(len(passed) / total * 100):.1f}%" if total else "0.0%"
    avg_latency = (
        int(sum(r.latency_ms for r in passed) / len(passed)) if passed else 0
    )

    logger.info(
        "model_health_check_completed",
        total=total,
        passed=len(passed),
        failed=len(failed),
        avg_latency_ms=avg_latency,
    )

    failed_message: str | None = None
    if failed:
        lines = [
            f"• `{r.model_id}` [{r.status}]: {r.error or 'no response'}"
            for r in failed
        ]
        failed_message = "\n".join(lines)

    await send_slack_alert(
        title=f"Model Health Check — {len(passed)}/{total} passed",
        fields=[
            {"label": "Timestamp", "value": datetime.now(UTC).isoformat()},
            {"label": "Pass Rate", "value": pass_rate},
            {"label": "Avg Latency (passing)", "value": f"{avg_latency}ms"},
        ],
        message=failed_message,
        notify_here=bool(failed),
    )

    return ModelHealthResponse(
        total=total,
        passed=len(passed),
        failed=len(failed),
        pass_rate=pass_rate,
        avg_latency_ms=avg_latency,
        results=results,
    )
