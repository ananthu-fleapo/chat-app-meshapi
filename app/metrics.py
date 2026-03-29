"""
Prometheus metrics for RouterV.

HTTP-level metrics (request count, latency, status codes) are auto-instrumented
by prometheus-fastapi-instrumentator and exposed at GET /metrics.

Custom RouterV metrics defined here cover the inference pipeline specifically:
upstream calls, token throughput, cost, and guardrail hits.

Usage
-----
Import and call the record_* helpers from the relevant modules.
All metrics are registered on the default prometheus_client registry.
Counters and histograms are module-level singletons — safe to import anywhere.
"""

from prometheus_client import Counter, Histogram

# ── Upstream inference ────────────────────────────────────────────────────────

UPSTREAM_REQUESTS = Counter(
    "routerv_upstream_requests_total",
    "Total inference requests forwarded to the upstream provider.",
    ["model", "status"],   # status: success | error
)

UPSTREAM_LATENCY = Histogram(
    "routerv_upstream_latency_seconds",
    "Latency of upstream inference calls in seconds.",
    ["model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# ── Token throughput ──────────────────────────────────────────────────────────

TOKENS_TOTAL = Counter(
    "routerv_tokens_total",
    "Total tokens processed (prompt + completion separately).",
    ["model", "token_type"],   # token_type: prompt | completion
)

# ── Cost ─────────────────────────────────────────────────────────────────────

COST_USD_TOTAL = Counter(
    "routerv_cost_usd_total",
    "Cumulative USD cost charged to users (using model_prices table).",
    ["model"],
)

# ── Guardrails ────────────────────────────────────────────────────────────────

RATE_LIMIT_HITS = Counter(
    "routerv_rate_limit_hits_total",
    "Number of requests rejected by the rate limiter.",
    ["limit_type"],   # limit_type: rpm | rpd
)

BALANCE_BLOCKS = Counter(
    "routerv_balance_blocks_total",
    "Number of requests rejected due to insufficient balance.",
)

AUTH_FAILURES = Counter(
    "routerv_auth_failures_total",
    "Number of authentication failures.",
    ["reason"],   # reason: invalid_key | suspended
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def record_inference(
    *,
    model: str,
    status: str,
    latency_ms: int,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cost_usd: float | None,
) -> None:
    """Record all inference-related metrics in one call. Safe to call from background tasks."""
    UPSTREAM_REQUESTS.labels(model=model, status=status).inc()
    UPSTREAM_LATENCY.labels(model=model).observe(latency_ms / 1000)

    if prompt_tokens:
        TOKENS_TOTAL.labels(model=model, token_type="prompt").inc(prompt_tokens)
    if completion_tokens:
        TOKENS_TOTAL.labels(model=model, token_type="completion").inc(completion_tokens)
    if cost_usd and cost_usd > 0:
        COST_USD_TOTAL.labels(model=model).inc(cost_usd)
