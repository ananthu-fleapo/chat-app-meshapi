"""
GET /status — public endpoint for the status page.

Queries Prometheus HTTP API for inference metrics and runs the same
Postgres + Redis health checks as /readyz.  Results are cached in Redis
for 30 seconds to avoid hammering Prometheus on every page load.

No auth required — this is a public, read-only endpoint.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings

logger = structlog.get_logger()
router = APIRouter(tags=["status"])

_CACHE_KEY = "status:v1"
_CACHE_TTL = 30  # seconds

# PromQL expressions ─────────────────────────────────────────────────────────
# Use a 24h rate window for scalars so sparse traffic still yields a value.
# Range query uses a 6h rate window per step to smooth over quiet periods.
#
# Excluded model patterns:
#   image    — *-image, *-image-* (Gemini Image, GPT-5 Image, etc.)
#   tts      — *-tts-*, tts-* (Qwen TTS, Gemini TTS)
#   audio    — *audio* (GPT-4o Audio, GPT Audio)
#   lyria    — *lyria* (Google Lyria music generation)
#   voxtral  — *voxtral* (Mistral voice models)
#
# Timeout exclusion: UPSTREAM_LATENCY now carries a `status` label so
# latency queries filter status="success", dropping timed-out requests
# (which are recorded as status="error") from the percentile calculation.
# NOTE: old series recorded before this change have no status label and are
# excluded automatically — percentiles will be based on new data only.

_EXCLUDE_MODELS = r'model!~".*(image|tts|audio|lyria|voxtral).*"'
_SUCCESS_LATENCY = f'status="success",{_EXCLUDE_MODELS}'

_Q_SUCCESS_RATE = (
    f'sum(rate(routerv_upstream_requests_total{{status="success",{_EXCLUDE_MODELS}}}[24h]))'
    f" / sum(rate(routerv_upstream_requests_total{{{_EXCLUDE_MODELS}}}[24h])) * 100"
)
_Q_P50 = (
    f"histogram_quantile(0.5,"
    f" sum(rate(routerv_upstream_latency_seconds_bucket{{{_SUCCESS_LATENCY}}}[24h])) by (le)) * 1000"
)
_Q_P99 = (
    f"histogram_quantile(0.99,"
    f" sum(rate(routerv_upstream_latency_seconds_bucket{{{_SUCCESS_LATENCY}}}[24h])) by (le)) * 1000"
)
_Q_UPTIME = "time() - process_start_time_seconds"

_Q_RANGE_P50 = (
    f"histogram_quantile(0.5,"
    f" sum(rate(routerv_upstream_latency_seconds_bucket{{{_SUCCESS_LATENCY}}}[6h])) by (le)) * 1000"
)
_Q_RANGE_P99 = (
    f"histogram_quantile(0.99,"
    f" sum(rate(routerv_upstream_latency_seconds_bucket{{{_SUCCESS_LATENCY}}}[6h])) by (le)) * 1000"
)

# Hourly success rate history (range query, 1h step, 24h window)
_Q_RANGE_SUCCESS_RATE = (
    f'sum(rate(routerv_upstream_requests_total{{status="success",{_EXCLUDE_MODELS}}}[1h]))'
    f' / sum(rate(routerv_upstream_requests_total{{{_EXCLUDE_MODELS}}}[1h])) * 100'
)

# Per-model error rate — returns only models where error rate > 5% in last 1h
_Q_FAILING_MODELS = (
    f'(sum by (model) (rate(routerv_upstream_requests_total{{status="error",{_EXCLUDE_MODELS}}}[1h]))'
    f' / sum by (model) (rate(routerv_upstream_requests_total{{{_EXCLUDE_MODELS}}}[1h])) * 100) > 5'
)


def _prom_value(result: dict[str, Any]) -> float | None:
    """Extract a scalar float from a Prometheus instant query result."""
    try:
        rows = result["data"]["result"]
        if not rows:
            return None
        raw = rows[0]["value"][1]
        val = float(raw)
        # NaN / Inf mean no data
        if val != val or val == float("inf") or val == float("-inf"):
            return None
        return val
    except Exception:  # noqa: BLE001
        return None


async def _prom_vector(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    """Return all series from a Prometheus instant vector query as [{labels, value}]."""
    try:
        resp = await client.get(
            "/api/v1/query",
            params={"query": query},
            timeout=5.0,
        )
        resp.raise_for_status()
        rows = resp.json()["data"]["result"]
        out = []
        for row in rows:
            val = float(row["value"][1])
            if val != val or val == float("inf"):
                continue
            out.append({"labels": row["metric"], "value": val})
        return out
    except Exception:  # noqa: BLE001
        return []


async def _prom_instant(client: httpx.AsyncClient, query: str) -> float | None:
    try:
        resp = await client.get(
            "/api/v1/query",
            params={"query": query},
            timeout=5.0,
        )
        resp.raise_for_status()
        return _prom_value(resp.json())
    except Exception:  # noqa: BLE001
        return None


async def _prom_range(
    client: httpx.AsyncClient,
    query: str,
    start: int,
    end: int,
    step: int,
) -> list[dict[str, Any]]:
    """Return [{ts, value}] from a Prometheus range query."""
    try:
        resp = await client.get(
            "/api/v1/query_range",
            params={"query": query, "start": start, "end": end, "step": step},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = data["data"]["result"]
        if not rows:
            return []
        return [
            {"ts": int(ts), "value": float(v) if float(v) == float(v) else None}
            for ts, v in rows[0]["values"]
        ]
    except Exception:  # noqa: BLE001
        return []


async def _fetch_metrics() -> dict[str, Any]:
    """Query Prometheus for all status metrics concurrently."""
    if not settings.prometheus_url:
        return {
            "metrics": None,
            "latency_history": None,
            "success_rate_history": None,
            "failing_models": None,
            "uptime_seconds": None,
        }

    now = int(datetime.now(UTC).timestamp())
    start = now - 86400  # 24h ago

    async with httpx.AsyncClient(base_url=settings.prometheus_url) as client:
        (
            success_rate,
            p50,
            p99,
            uptime,
            range_p50_raw,
            range_p99_raw,
            range_sr_raw,
            failing_raw,
        ) = await asyncio.gather(
            _prom_instant(client, _Q_SUCCESS_RATE),
            _prom_instant(client, _Q_P50),
            _prom_instant(client, _Q_P99),
            _prom_instant(client, _Q_UPTIME),
            _prom_range(client, _Q_RANGE_P50, start, now, step=1800),
            _prom_range(client, _Q_RANGE_P99, start, now, step=1800),
            _prom_range(client, _Q_RANGE_SUCCESS_RATE, start, now, step=3600),
            _prom_vector(client, _Q_FAILING_MODELS),
        )

    # Latency history — merge p50/p99 by timestamp
    p99_by_ts = {row["ts"]: row["value"] for row in range_p99_raw}
    latency_history = [
        {
            "ts": row["ts"],
            "p50_ms": round(row["value"]) if row["value"] is not None else None,
            "p99_ms": round(p99_by_ts[row["ts"]]) if p99_by_ts.get(row["ts"]) is not None else None,
        }
        for row in range_p50_raw
    ]

    # Success rate history — hourly buckets
    success_rate_history = [
        {"ts": row["ts"], "success_rate_pct": round(row["value"], 2)}
        for row in range_sr_raw
        if row["value"] is not None
    ]

    # Failing models — sort by error rate descending
    failing_models = sorted(
        [
            {
                "model": row["labels"].get("model", "unknown"),
                "error_rate_pct": round(row["value"], 1),
            }
            for row in failing_raw
        ],
        key=lambda x: x["error_rate_pct"],
        reverse=True,
    )

    metrics: dict[str, Any] = {
        "success_rate_pct": round(success_rate, 2) if success_rate is not None else None,
        "p50_ms": round(p50) if p50 is not None else None,
        "p99_ms": round(p99) if p99 is not None else None,
    }

    return {
        "metrics": metrics,
        "latency_history": latency_history,
        "success_rate_history": success_rate_history,
        "failing_models": failing_models,
        "uptime_seconds": round(uptime) if uptime is not None else None,
    }


async def _health_checks() -> tuple[dict[str, dict[str, str]], bool]:
    """Run Postgres SELECT 1 + Redis PING. Returns (services_dict, all_ok)."""
    from app.cache.redis_client import get_redis
    from app.db.engine import get_engine
    import sqlalchemy as sa

    services: dict[str, dict[str, str]] = {
        "api": {"status": "ok"},
        "postgres": {"status": "unknown"},
        "redis": {"status": "unknown"},
    }
    all_ok = True

    # Postgres
    try:
        engine = get_engine()
        if engine is not None:
            async with engine.connect() as conn:
                await conn.execute(sa.text("SELECT 1"))
            services["postgres"] = {"status": "ok"}
        else:
            services["postgres"] = {"status": "not_configured"}
    except Exception as exc:  # noqa: BLE001
        services["postgres"] = {"status": "error"}
        all_ok = False
        logger.warning("status_postgres_check_failed", error=str(exc))

    # Redis
    try:
        redis = get_redis()
        if redis is not None:
            await redis.ping()
            services["redis"] = {"status": "ok"}
        else:
            services["redis"] = {"status": "not_configured"}
    except Exception as exc:  # noqa: BLE001
        services["redis"] = {"status": "error"}
        all_ok = False
        logger.warning("status_redis_check_failed", error=str(exc))

    return services, all_ok


def _overall_status(
    all_healthy: bool,
    metrics: dict[str, Any] | None,
) -> str:
    if not all_healthy:
        return "down"
    if metrics:
        sr = metrics.get("success_rate_pct")
        if sr is not None and sr < 80:
            return "degraded"
    return "operational"


@router.get("/status", include_in_schema=True)
async def get_status() -> JSONResponse:
    """
    Public service status endpoint.

    Returns overall health, per-service checks, and inference metrics
    sourced from Prometheus.  Cached in Redis for 30 s.
    """
    from app.cache.redis_client import get_redis

    # ── Cache hit ─────────────────────────────────────────────────────────────
    redis = get_redis()
    if redis is not None:
        try:
            cached = await redis.get(_CACHE_KEY)
            if cached:
                return JSONResponse(content=json.loads(cached))
        except Exception:  # noqa: BLE001
            pass

    # ── Fetch concurrently ────────────────────────────────────────────────────
    try:
        (services, all_healthy), prom = await asyncio.gather(
            _health_checks(),
            _fetch_metrics(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("status_fetch_failed", error=str(exc))
        return JSONResponse(
            content={
                "status": "down",
                "metrics": None,
                "latency_history": None,
                "success_rate_history": None,
                "failing_models": None,
                "uptime_seconds": None,
                "checked_at": datetime.now(UTC).isoformat(),
            }
        )

    payload: dict[str, Any] = {
        "status": _overall_status(all_healthy, prom.get("metrics")),
        "metrics": prom.get("metrics"),
        "latency_history": prom.get("latency_history"),
        "success_rate_history": prom.get("success_rate_history"),
        "failing_models": prom.get("failing_models"),
        "uptime_seconds": prom.get("uptime_seconds"),
        "checked_at": datetime.now(UTC).isoformat(),
    }

    # ── Cache write ───────────────────────────────────────────────────────────
    if redis is not None:
        try:
            await redis.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(payload))
        except Exception:  # noqa: BLE001
            pass

    return JSONResponse(content=payload)
