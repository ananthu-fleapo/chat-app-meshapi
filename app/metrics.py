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

from prometheus_client import Counter, Histogram, Gauge

# ── Upstream inference ────────────────────────────────────────────────────────

UPSTREAM_REQUESTS = Counter(
    "routerv_upstream_requests_total",
    "Total inference requests forwarded to the upstream provider.",
    ["model", "status"],   # status: success | error
)

UPSTREAM_LATENCY = Histogram(
    "routerv_upstream_latency_seconds",
    "Latency of upstream inference calls in seconds.",
    ["model", "status"],   # status: success | error — allows filtering timeouts from percentiles
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

# ── Database ──────────────────────────────────────────────────────────────────

SQLALCHEMY_POOL_SIZE = Gauge(
    "sqlalchemy_pool_size",
    "Total database connection pool size",
)

SQLALCHEMY_POOL_CHECKED_OUT = Gauge(
    "sqlalchemy_pool_checked_out",
    "Number of checked out database connections",
)

SQLALCHEMY_POOL_OVERFLOW = Gauge(
    "sqlalchemy_pool_overflow",
    "Number of overflow database connections",
)

SQLALCHEMY_QUERY_DURATION = Histogram(
    "sqlalchemy_query_duration_seconds",
    "Database query execution time in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── Process ───────────────────────────────────────────────────────────────────

PROCESS_CPU_CORES = Gauge(
    "process_cpu_cores",
    "Number of CPU cores available to the process",
)

PROCESS_TOTAL_MEMORY_BYTES = Gauge(
    "process_total_memory_bytes",
    "Total system memory available in bytes",
)

# ── Redis ─────────────────────────────────────────────────────────────────────

REDIS_CONNECTED_CLIENTS = Gauge(
    "redis_connected_clients",
    "Number of connected Redis clients",
)

REDIS_MEMORY_USED_BYTES = Gauge(
    "redis_memory_used_bytes",
    "Redis memory usage in bytes",
)

REDIS_MEMORY_MAX_BYTES = Gauge(
    "redis_memory_max_bytes",
    "Redis max memory limit in bytes",
)

REDIS_COMMANDS_PROCESSED_SNAPSHOT = Gauge(
    "redis_total_commands_processed_snapshot",
    "Raw snapshot of Redis total_commands_processed (monotonic, not a rate metric)",
)


# ── Auto Router ───────────────────────────────────────────────────────────────

AUTO_ROUTER_REQUESTS = Counter(
    "gateway_auto_router_requests_total",
    "Total requests routed through the Auto Router.",
)

AUTO_ROUTER_FALLBACK = Counter(
    "gateway_auto_router_fallback_total",
    "Auto Router requests that fell back to the configured default model.",
    ["reason"],  # empty_registry | classifier_error | classifier_timeout | invalid_response
)

AUTO_ROUTER_CLASSIFIER_LATENCY = Histogram(
    "gateway_auto_router_classifier_latency_ms",
    "Classifier LLM call latency in milliseconds.",
    buckets=[50, 100, 250, 500, 1000, 2000, 3000, 5000, 10000],
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
    UPSTREAM_LATENCY.labels(model=model, status=status).observe(latency_ms / 1000)

    if prompt_tokens:
        TOKENS_TOTAL.labels(model=model, token_type="prompt").inc(prompt_tokens)
    if completion_tokens:
        TOKENS_TOTAL.labels(model=model, token_type="completion").inc(completion_tokens)
    if cost_usd and cost_usd > 0:
        COST_USD_TOTAL.labels(model=model).inc(cost_usd)


def update_pool_metrics(engine) -> None:
    """Update SQLAlchemy pool metrics from engine. Call periodically from a background task."""
    if engine and hasattr(engine, 'pool'):
        pool = engine.pool
        try:
            SQLALCHEMY_POOL_SIZE.set(pool.size())
            SQLALCHEMY_POOL_CHECKED_OUT.set(pool.checkedout())
            SQLALCHEMY_POOL_OVERFLOW.set(pool.overflow())
        except Exception:
            # Fail silently if pool metrics are unavailable
            pass


async def update_redis_metrics(redis) -> None:
    """Update Redis metrics from redis client. Call periodically from a background task."""
    if redis is None:
        return

    try:
        info = await redis.info()
        REDIS_CONNECTED_CLIENTS.set(info.get("connected_clients", 0))
        REDIS_MEMORY_USED_BYTES.set(info.get("used_memory", 0))
        REDIS_MEMORY_MAX_BYTES.set(info.get("maxmemory", 0))
        REDIS_COMMANDS_PROCESSED_SNAPSHOT.set(info.get("total_commands_processed", 0))
    except Exception:
        # Fail silently if Redis metrics are unavailable (e.g., cloud Redis, network issues)
        pass
