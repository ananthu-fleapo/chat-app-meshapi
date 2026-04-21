"""
Model Health Check — POST /v1/model-health/run

Tests every enabled model with a minimal prompt and reports pass/fail results
to Slack. Intended to be triggered by Cloud Scheduler every 6 hours.

Auth: WEBHOOK_API_KEY bearer token (same as /v1/fx-rates/refresh).

Cloud Scheduler config:
    Schedule:  0 */6 * * *
    URL:       POST https://<routersvc-url>/v1/model-health/run
    Header:    Authorization: Bearer <WEBHOOK_API_KEY>

Self-calling mode:
    When HEALTH_CHECK_SELF_URL and HEALTH_CHECK_API_KEY are set, tests call
    the live inference endpoints (e.g. https://api.meshapi.ai/v1/chat/completions)
    so the full user flow — auth, routing, balance, usage logging — is exercised.
"""

from __future__ import annotations

import asyncio
import contextvars
import math
import statistics
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import structlog
import structlog.contextvars
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sqlalchemy import select

from app.auth.dependencies import verify_webhook_key
from app.config import settings
from app.db.engine import get_session_factory
from app.db.models import Model, ModelPrice
from app.notifications.slack import send_slack_alert
from app.storage.gcs import upload_csv

logger = structlog.get_logger()
router = APIRouter(tags=["model-health"])

_CONCURRENCY = 5
_TIMEOUT_S = 60.0
_MAX_TOKENS = 1024

# ── Self-calling httpx client ─────────────────────────────────────────────────

_self_client: httpx.AsyncClient | None = None


def _get_self_client() -> httpx.AsyncClient:
    global _self_client
    if _self_client is None:
        _self_client = httpx.AsyncClient(
            base_url=settings.health_check_self_url.rstrip("/"),
            headers={"Authorization": f"Bearer {settings.health_check_api_key}"},
            timeout=httpx.Timeout(_TIMEOUT_S),
        )
    return _self_client


# ── Rate limiter ─────────────────────────────────────────────────────────────


class _RateLimiter:
    """Fixed-window counter: allows up to `rpm` requests to burst immediately,
    then blocks until the 120s window resets."""

    def __init__(self, rpm: int) -> None:
        self._rpm = rpm
        self._count = 0
        self._window_start = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if now - self._window_start >= 120.0:
                self._window_start = now
                self._count = 0
            if self._count >= self._rpm:
                wait = 120.0 - (time.monotonic() - self._window_start)
                if wait > 0:
                    await asyncio.sleep(wait)
                self._window_start = time.monotonic()
                self._count = 0
            self._count += 1


# ── Context & endpoint specs ──────────────────────────────────────────────────


@dataclass
class ModelTestContext:
    model_id: str
    model_type: str  # default "unknown" if DB row missing
    provider: str


@dataclass
class EndpointSpec:
    test_type: str
    path: str
    payload_fn: Callable[[ModelTestContext], dict]


_ENDPOINT_SPECS: list[EndpointSpec] = [
    EndpointSpec(
        test_type="completions",
        path="/v1/chat/completions",
        payload_fn=lambda ctx: {
            "model": ctx.model_id,
            "messages": [{"role": "user", "content": "Say hi"}],
            "max_tokens": _MAX_TOKENS,
            "stream": False,
        },
    ),
    EndpointSpec(
        test_type="responses",
        path="/v1/responses",
        payload_fn=lambda ctx: {
            "model": ctx.model_id,
            "input": "Say hi",
            "max_output_tokens": _MAX_TOKENS,
            "stream": False,
        },
    ),
    EndpointSpec(
        test_type="embeddings",
        path="/v1/embeddings",
        payload_fn=lambda ctx: {
            "model": ctx.model_id,
            "input": "Hello",
        },
    ),
]

_SPEC_BY_TYPE: dict[str, EndpointSpec] = {s.test_type: s for s in _ENDPOINT_SPECS}


# ── Response schema ───────────────────────────────────────────────────────────


class ModelHealthResult(BaseModel):
    model_id: str
    model_type: str = "unknown"
    test_type: str = "completions"  # "completions" | "responses" | "embeddings"
    status: str  # "pass" | "fail" | "timeout" | "degraded"
    latency_ms: int
    error: str | None = None
    provider: str | None = None
    upstream_status: int | None = None
    upstream_body: str | None = None  # first 300 chars of upstream error response body


class ModelHealthResponse(BaseModel):
    total: int
    passed: int
    failed: int
    pass_rate: str
    avg_latency_ms: int
    latency_by_model_type: dict[
        str, dict
    ]  # {"text/completions": {"p50":..,"p95":..,"count":..}}
    results: list[ModelHealthResult]


# ── Internals ─────────────────────────────────────────────────────────────────


def _extract_upstream_status(exc: Exception) -> int | None:
    # httpx.HTTPStatusError carries .response directly
    if hasattr(exc, "response"):
        return getattr(exc.response, "status_code", None)
    cause = getattr(exc, "__cause__", None)
    return getattr(getattr(cause, "response", None), "status_code", None)


def _extract_upstream_body(exc: Exception) -> str | None:
    resp = getattr(exc, "response", None) or getattr(
        getattr(exc, "__cause__", None), "response", None
    )
    body = getattr(resp, "text", None)
    return body[:300] if body else None


def _percentile(sorted_lats: list[int], p: float) -> int:
    if not sorted_lats:
        return 0
    idx = max(0, math.ceil(p * len(sorted_lats)) - 1)
    return sorted_lats[idx]


def _latency_stats(lats: list[int]) -> dict:
    s = sorted(lats)
    return {
        "p50": int(statistics.median(s)),
        "p95": _percentile(s, 0.95),
        "count": len(s),
    }


async def _test_endpoint(
    ctx: ModelTestContext,
    spec: EndpointSpec,
    rate_limiter: _RateLimiter | None = None,
) -> ModelHealthResult:
    """Test a single inference endpoint for one model. Never raises."""
    if rate_limiter is not None:
        await rate_limiter.acquire()
    structlog.contextvars.bind_contextvars(
        model_id=ctx.model_id, provider=ctx.provider, test_type=spec.test_type
    )
    start = time.monotonic()
    try:
        client = _get_self_client()
        resp = await client.post(spec.path, json=spec.payload_fn(ctx))
        resp.raise_for_status()
        return ModelHealthResult(
            model_id=ctx.model_id,
            model_type=ctx.model_type,
            test_type=spec.test_type,
            status="pass",
            latency_ms=int((time.monotonic() - start) * 1000),
            provider=ctx.provider,
        )
    except httpx.TimeoutException:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "model_health_timeout",
            test_type=spec.test_type,
            timeout_s=_TIMEOUT_S,
            latency_ms=latency_ms,
        )
        return ModelHealthResult(
            model_id=ctx.model_id,
            model_type=ctx.model_type,
            test_type=spec.test_type,
            status="timeout",
            latency_ms=latency_ms,
            provider=ctx.provider,
        )
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        upstream_status = _extract_upstream_status(exc)
        upstream_body = _extract_upstream_body(exc)
        status = "degraded" if upstream_status == 429 else "fail"
        log_fn = logger.warning if status == "degraded" else logger.exception
        log_fn(
            "model_health_fail",
            test_type=spec.test_type,
            latency_ms=latency_ms,
            exc_type=type(exc).__name__,
            error=str(exc),
            upstream_status=upstream_status,
            upstream_body=upstream_body,
        )
        return ModelHealthResult(
            model_id=ctx.model_id,
            model_type=ctx.model_type,
            test_type=spec.test_type,
            status=status,
            latency_ms=latency_ms,
            error=str(exc),
            provider=ctx.provider,
            upstream_status=upstream_status,
            upstream_body=upstream_body,
        )


def _build_csv(results: list[ModelHealthResult], run_ts: datetime) -> str:
    """Serialise all health-check results to a UTF-8 CSV string."""
    import csv
    import io

    fieldnames = [
        "run_timestamp",
        "model_id",
        "model_type",
        "test_type",
        "status",
        "provider",
        "latency_ms",
        "upstream_status",
        "upstream_body",
        "error",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for r in results:
        writer.writerow(
            {
                "run_timestamp": run_ts.isoformat(),
                "model_id": r.model_id,
                "model_type": r.model_type,
                "test_type": r.test_type,
                "status": r.status,
                "provider": r.provider or "",
                "latency_ms": r.latency_ms,
                "upstream_status": (
                    r.upstream_status if r.upstream_status is not None else ""
                ),
                "upstream_body": r.upstream_body or "",
                "error": r.error or "",
            }
        )
    return buf.getvalue()


async def _upload_results_csv(
    results: list[ModelHealthResult], run_ts: datetime
) -> str | None:
    """Build and upload the results CSV; return the GCS URL or None on failure."""
    bucket = settings.gcs_health_check_bucket
    if not bucket:
        return None

    csv_content = _build_csv(results, run_ts)
    date_prefix = run_ts.strftime("%Y-%m-%d")
    ts_slug = run_ts.strftime("%Y%m%dT%H%M%SZ")
    blob_name = f"health_check/{date_prefix}/{ts_slug}.csv"

    return await upload_csv(bucket, blob_name, csv_content)


async def _guarded(
    coro: Coroutine,
    ctx: ModelTestContext,
    test_type: str,
) -> ModelHealthResult:
    """Catch any unexpected exception that escapes a test function.

    The individual test functions already have comprehensive try/except blocks,
    so this should never fire in normal operation. If it does, the result is
    surfaced as a "fail" in the Slack report rather than silently dropped.
    """
    try:
        return await coro
    except BaseException as exc:
        logger.error(
            "model_health_task_crashed",
            model_id=ctx.model_id,
            model_type=ctx.model_type,
            test_type=test_type,
            provider=ctx.provider,
            error=str(exc),
            exc_info=exc,
        )
        return ModelHealthResult(
            model_id=ctx.model_id,
            model_type=ctx.model_type,
            test_type=test_type,
            status="fail",
            latency_ms=0,
            error=f"internal error: {exc}",
            provider=ctx.provider,
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
    logger.info(
        "model_health_check_started",
        mode="self" if settings.health_check_self_url else "direct",
    )

    if not settings.health_check_self_url or not settings.health_check_api_key:
        logger.error(
            "model_health_misconfigured",
            reason="HEALTH_CHECK_SELF_URL and HEALTH_CHECK_API_KEY must both be set",
        )
        raise HTTPException(
            status_code=503,
            detail="HEALTH_CHECK_SELF_URL and HEALTH_CHECK_API_KEY are required for model health checks",
        )

    # Query all enabled models joined with ALL their model_prices rows so that
    # every (model, provider) combination is tested independently.
    # Outer join preserves models that have no pricing row at all (NULLs →
    # capability defaults applied below).
    async with get_session_factory()() as session:
        result = await session.execute(
            select(
                Model.model_id,
                Model.model_type,
                ModelPrice.provider,
                ModelPrice.supports_completions_api,
                ModelPrice.supports_responses_api,
                ModelPrice.supports_embeddings_api,
            )
            .outerjoin(ModelPrice, Model.model_id == ModelPrice.model_id)
            .where(Model.is_enabled.is_(True))
            .order_by(Model.model_id, ModelPrice.provider)
        )
        model_rows = result.all()
    logger.info("model_health_models_fetched", count=len(model_rows))

    # Build a flat list of (ctx, test_type, coro) tuples.
    rate_limiter = _RateLimiter(settings.health_check_rpm)
    Task = tuple[ModelTestContext, str, Coroutine]
    tasks: list[Task] = []
    for row in model_rows:
        ctx = ModelTestContext(
            model_id=row.model_id,
            model_type=row.model_type or "unknown",
            provider=row.provider or "openrouter",
        )
        # Null means no pricing row — default to completions=True, others=False.
        supports_completions = (
            row.supports_completions_api
            if row.supports_completions_api is not None
            else True
        )
        supports_responses = (
            row.supports_responses_api
            if row.supports_responses_api is not None
            else False
        )
        supports_embeddings = (
            row.supports_embeddings_api
            if row.supports_embeddings_api is not None
            else False
        )

        enabled = {
            "completions": supports_completions,
            "responses": supports_responses,
            "embeddings": supports_embeddings,
        }
        any_enabled = False
        for test_type, supported in enabled.items():
            if supported:
                spec = _SPEC_BY_TYPE[test_type]
                tasks.append((ctx, test_type, _test_endpoint(ctx, spec, rate_limiter)))
                any_enabled = True
        if not any_enabled:
            # No flags set at all — fall back to a completions test.
            tasks.append(
                (
                    ctx,
                    "completions",
                    _test_endpoint(ctx, _SPEC_BY_TYPE["completions"], rate_limiter),
                )
            )

    # Batched concurrency — _CONCURRENCY tasks tested in parallel per batch.
    results: list[ModelHealthResult] = []
    queue = list(tasks)
    while queue:
        batch = queue[:_CONCURRENCY]
        queue = queue[_CONCURRENCY:]
        batch_results = await asyncio.gather(
            *[
                asyncio.create_task(
                    _guarded(coro, ctx, test_type),
                    context=contextvars.copy_context(),
                )
                for ctx, test_type, coro in batch
            ],
            return_exceptions=False,  # _guarded never raises
        )
        results.extend(batch_results)

    passed = [r for r in results if r.status == "pass"]
    timeouts = [r for r in results if r.status == "timeout"]
    pure_fails = [r for r in results if r.status == "fail"]
    degraded = [r for r in results if r.status == "degraded"]
    # "not working" = genuine failures + timeouts; degraded (429) excluded
    not_working = pure_fails + timeouts
    total = len(results)
    pass_rate = f"{(len(passed) / total * 100):.1f}%" if total else "0.0%"
    avg_latency = int(sum(r.latency_ms for r in passed) / len(passed)) if passed else 0

    # Per-(model_type/test_type) p50/p95 latency stats (passing results only).
    type_lats: dict[str, list[int]] = defaultdict(list)
    for r in passed:
        type_lats[f"{r.model_type}/{r.test_type}"].append(r.latency_ms)
    latency_by_model_type = {t: _latency_stats(lats) for t, lats in type_lats.items()}

    # Slowest passing result per (model_type/test_type) for Slack body
    slowest: dict[str, ModelHealthResult] = {}
    for r in passed:
        key = f"{r.model_type}/{r.test_type}"
        if key not in slowest or r.latency_ms > slowest[key].latency_ms:
            slowest[key] = r

    logger.info(
        "model_health_check_completed",
        total=total,
        passed=len(passed),
        degraded=len(degraded),
        failed=len(pure_fails),
        timeouts=len(timeouts),
        avg_latency_ms=avg_latency,
    )

    # Upload full results CSV to GCS (best-effort — does not block Slack alert).
    run_ts = datetime.now(UTC)
    csv_url = await _upload_results_csv(results, run_ts)

    # Build Slack message — group by status for clarity
    non_passing = not_working + degraded
    slack_lines: list[str] = []
    if non_passing:
        for r in non_passing:
            detail = f" {r.provider}" if r.provider else ""
            if r.upstream_status:
                detail += f" → HTTP {r.upstream_status}"
            if r.status == "timeout":
                detail += f" ({_TIMEOUT_S}s timeout)"
            err_str = (
                f": {r.error}"
                if r.error and r.status not in ("timeout", "degraded")
                else ""
            )
            slack_lines.append(
                f"• `{r.model_id}` [{r.test_type}] [{r.status}]{detail}{err_str}"
            )

    if slowest:
        slack_lines.append("")
        slack_lines.append("*Slowest passing model per type:*")
        for key, r in sorted(slowest.items()):
            slack_lines.append(f"• `{r.model_id}` ({key}) — {r.latency_ms}ms")

    slack_body = "\n".join(slack_lines) if slack_lines else None

    fields: list[dict[str, str]] = [
        {"label": "Timestamp", "value": run_ts.isoformat()},
        {"label": "Pass Rate", "value": pass_rate},
        {"label": "Avg Latency (passing)", "value": f"{avg_latency}ms"},
        {"label": "Failures", "value": str(len(pure_fails))},
        {"label": "Timeouts", "value": str(len(timeouts))},
        {"label": "Degraded (rate-limited)", "value": str(len(degraded))},
    ]
    for key, stats in sorted(latency_by_model_type.items()):
        fields.append(
            {
                "label": f"Latency — {key.upper()}",
                "value": f"p50: {stats['p50']}ms | p95: {stats['p95']}ms | n={stats['count']}",
            }
        )
    if csv_url:
        fields.append({"label": "Full Results (CSV)", "value": csv_url})

    await send_slack_alert(
        title=f"Model Health Check — {len(passed)}/{total} passed",
        fields=fields,
        message=slack_body,
        notify_here=bool(
            not_working
        ),  # only page for genuine failures/timeouts, not 429s
    )

    return ModelHealthResponse(
        total=total,
        passed=len(passed),
        failed=len(not_working),
        pass_rate=pass_rate,
        avg_latency_ms=avg_latency,
        latency_by_model_type=latency_by_model_type,
        results=results,
    )
