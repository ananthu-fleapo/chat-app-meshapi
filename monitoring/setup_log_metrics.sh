#!/usr/bin/env bash
# =============================================================================
# RouterV — Cloud Logging: Log-Based Metrics
# =============================================================================
# Run once per GCP project to create the log-based metrics used by alert
# policies and dashboards.
#
# Usage:
#   export PROJECT_ID=your-gcp-project-id
#   bash monitoring/setup_log_metrics.sh
#
# All metrics are DELTA (count over window) unless stated otherwise.
# All filters scope to our service via the "service=routersvc" label we stamp
# on every log line in logging_config.py.
# =============================================================================

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID before running this script}"

gcloud config set project "$PROJECT_ID"

echo "Creating log-based metrics for project: $PROJECT_ID"

# ── 1. HTTP 5xx errors ────────────────────────────────────────────────────────
# Source: access log emitted by RequestIdMiddleware for every request.
# Fires on any response with status >= 500.  Used by the 5xx error rate alert.
gcloud logging metrics create routersvc_http_5xx \
  --description="RouterV: HTTP 5xx responses" \
  --log-filter='
    resource.type="cloud_run_revision"
    jsonPayload.service="routersvc"
    jsonPayload.message="http_request"
    jsonPayload.status>=500
  ' 2>/dev/null || echo "routersvc_http_5xx already exists, skipping"

# ── 2. Upstream errors (502 / 504) ────────────────────────────────────────────
# Source: exception handler log (error_code field).
# Distinct from 5xx because upstream errors are usually provider-side; a spike
# here may not require code changes but does require provider investigation.
gcloud logging metrics create routersvc_upstream_errors \
  --description="RouterV: upstream provider errors (502/504)" \
  --log-filter='
    resource.type="cloud_run_revision"
    jsonPayload.service="routersvc"
    jsonPayload.message="request_error"
    jsonPayload.error_code=("upstream_error" OR "gateway_timeout")
  ' 2>/dev/null || echo "routersvc_upstream_errors already exists, skipping"

# ── 3. Rate limit exceeded (429) ─────────────────────────────────────────────
# Source: exception handler log.
# Normal background noise; alert fires if a single key is hammering the limit
# (possible abuse or misconfigured client).
gcloud logging metrics create routersvc_rate_limit_exceeded \
  --description="RouterV: rate limit exceeded (429)" \
  --log-filter='
    resource.type="cloud_run_revision"
    jsonPayload.service="routersvc"
    jsonPayload.message="rate_limit_exceeded"
  ' 2>/dev/null || echo "routersvc_rate_limit_exceeded already exists, skipping"

# ── 4. Auth errors (401 / 403) ────────────────────────────────────────────────
# Source: exception handler log.
# A sustained spike indicates credential brute-force or a client misconfiguration.
gcloud logging metrics create routersvc_auth_errors \
  --description="RouterV: auth failures (401/403)" \
  --log-filter='
    resource.type="cloud_run_revision"
    jsonPayload.service="routersvc"
    jsonPayload.message="auth_error"
  ' 2>/dev/null || echo "routersvc_auth_errors already exists, skipping"

# ── 5. Usage log failures ─────────────────────────────────────────────────────
# Source: usage/logger.py silently swallows errors but emits usage_log_failed.
# Any occurrence means we're losing billing/audit data — needs immediate attention.
gcloud logging metrics create routersvc_usage_log_failed \
  --description="RouterV: usage event failed to persist" \
  --log-filter='
    resource.type="cloud_run_revision"
    jsonPayload.service="routersvc"
    jsonPayload.message="usage_log_failed"
  ' 2>/dev/null || echo "routersvc_usage_log_failed already exists, skipping"

# ── 6. Inference latency distribution ─────────────────────────────────────────
# Source: inference_complete / stream_complete log from inference.py.
# DISTRIBUTION type — lets us alert on p50/p95/p99 rather than average.
# Buckets: exponential growth from 100ms up to ~300s.
gcloud logging metrics create routersvc_inference_latency_ms \
  --description="RouterV: inference request latency (ms)" \
  --log-filter='
    resource.type="cloud_run_revision"
    jsonPayload.service="routersvc"
    jsonPayload.message=("inference_complete" OR "stream_complete")
    jsonPayload.status="success"
  ' \
  --value-extractor='EXTRACT(jsonPayload.latency_ms)' \
  --metric-kind=DELTA \
  --value-type=DISTRIBUTION \
  --buckets-type=exponential \
  --buckets-num-finite-buckets=20 \
  --buckets-scale=100 \
  --buckets-growth-factor=2 \
  2>/dev/null || echo "routersvc_inference_latency_ms already exists, skipping"

# ── 7. Spend cap hits (402) ───────────────────────────────────────────────────
# Source: exception handler, error_code=spend_limit_exceeded.
# Useful to know which owners are hitting caps — informs pricing conversations.
gcloud logging metrics create routersvc_spend_cap_exceeded \
  --description="RouterV: spend cap exceeded (402)" \
  --log-filter='
    resource.type="cloud_run_revision"
    jsonPayload.service="routersvc"
    jsonPayload.error_code="spend_limit_exceeded"
  ' 2>/dev/null || echo "routersvc_spend_cap_exceeded already exists, skipping"

# ── 8. Redis fail-open events ────────────────────────────────────────────────
# Source: rate_limiter.py logs redis_unavailable at WARNING when Redis is down.
# If this fires in prod, rate limiting is disabled — requires urgent fix.
gcloud logging metrics create routersvc_redis_fail_open \
  --description="RouterV: Redis unavailable (rate limiting disabled)" \
  --log-filter='
    resource.type="cloud_run_revision"
    jsonPayload.service="routersvc"
    jsonPayload.message="redis_unavailable"
  ' 2>/dev/null || echo "routersvc_redis_fail_open already exists, skipping"

echo ""
echo "✓ All log-based metrics created."
echo "  View at: https://console.cloud.google.com/logs/metrics?project=$PROJECT_ID"
