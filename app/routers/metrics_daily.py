"""
Daily Metrics Summary — POST /v1/metrics/daily-summary

Aggregates daily business metrics (users onboarded, requests processed,
success/failure rates, revenue, and payments received) and sends to Slack.
Intended to be triggered by Cloud Scheduler daily at 10 AM IST.

Auth: WEBHOOK_API_KEY bearer token (same as /v1/model-health/run).

Cloud Scheduler config:
    Schedule:  0 10 * * *
    URL:       POST https://<routersvc-url>/v1/metrics/daily-summary
    Header:    Authorization: Bearer <WEBHOOK_API_KEY>
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.analytics.payment_exprs import fx_rate_subquery
from app.auth.dependencies import verify_webhook_key
from app.db.engine import get_session_factory
from app.db.models import Model, PaymentEvent, UsageEvent, User
from app.notifications.slack import send_slack_alert

IST = ZoneInfo("Asia/Kolkata")

logger = structlog.get_logger()
router = APIRouter(tags=["metrics"])


# ── Response schema ───────────────────────────────────────────────────────────


class DailySummaryMetrics(BaseModel):
    users_onboarded: int
    unique_active_users: int
    requests_processed: int
    successful_requests: int
    failed_requests: int
    pending_requests: int
    success_rate: str  # e.g., "98.5%"
    failure_rate: str
    pending_rate: str
    revenue_usd: float
    payments_received_usd: float
    coupon_discounts_usd: float
    error_code_counts: dict[str, int]  # error_code → count, sorted by count desc
    latency_by_model_type: dict[str, dict] = {}  # model_type → {p50, p95, count}
    timestamp: datetime
    start_ist: datetime  # Start of the 10AM–10AM IST window


# ── Internals ─────────────────────────────────────────────────────────────────


async def _get_daily_metrics() -> DailySummaryMetrics:
    """Fetch all daily metrics from database.

    Returns aggregated counts and rates for the current UTC day.
    Never raises; returns zeros if no data found.
    """
    now_ist = datetime.now(IST)

    # Always report the last completed 8AM→8AM IST window.
    today_8am = now_ist.replace(hour=8, minute=0, second=0, microsecond=0)
    end_ist = today_8am if now_ist >= today_8am else today_8am - timedelta(days=1)
    start_ist = end_ist - timedelta(days=1)

    # Convert back to UTC for DB queries
    today_start = start_ist.astimezone(UTC)
    today_end = end_ist.astimezone(UTC)

    async with get_session_factory()() as session:
        # Query 1: Users onboarded today
        users_result = await session.execute(
            select(func.count(User.id)).where(
                User.created_at >= today_start, User.created_at < today_end
            )
        )
        users_onboarded = users_result.scalar() or 0

        # Query 1b: Unique users who made at least one request
        unique_users_result = await session.execute(
            select(func.count(func.distinct(UsageEvent.user_id))).where(
                UsageEvent.created_at >= today_start,
                UsageEvent.created_at < today_end,
                UsageEvent.user_id.isnot(None),
            )
        )
        unique_active_users = unique_users_result.scalar() or 0

        # Query 2: Requests and success/failure rates
        usage_result = await session.execute(
            select(
                func.count(UsageEvent.id).label("total"),
                func.count(UsageEvent.id).filter(UsageEvent.status == "success").label("success"),
                func.count(UsageEvent.id).filter(UsageEvent.status == "error").label("failed"),
                func.count(UsageEvent.id).filter(UsageEvent.status == "pending").label("pending"),
            ).where(UsageEvent.created_at >= today_start, UsageEvent.created_at < today_end)
        )
        usage_row = usage_result.one()
        requests_processed = usage_row.total or 0
        successful_requests = usage_row.success or 0
        failed_requests = usage_row.failed or 0
        pending_requests = usage_row.pending or 0

        # Calculate rates
        if requests_processed > 0:
            success_rate = f"{(successful_requests / requests_processed * 100):.1f}%"
            failure_rate = f"{(failed_requests / requests_processed * 100):.1f}%"
            pending_rate = f"{(pending_requests / requests_processed * 100):.1f}%"
        else:
            success_rate = "0.0%"
            failure_rate = "0.0%"
            pending_rate = "0.0%"

        # Query 3: Error code breakdown (only rows where error_code is set)
        error_code_result = await session.execute(
            select(
                UsageEvent.error_code,
                func.count(UsageEvent.id).label("cnt"),
            )
            .where(
                UsageEvent.created_at >= today_start,
                UsageEvent.created_at < today_end,
                UsageEvent.error_code.isnot(None),
            )
            .group_by(UsageEvent.error_code)
            .order_by(func.count(UsageEvent.id).desc())
        )
        error_code_counts: dict[str, int] = {
            row.error_code: row.cnt for row in error_code_result.all()
        }

        # Query 4: Revenue (all requests)
        revenue_result = await session.execute(
            select(func.sum(UsageEvent.cost_usd)).where(
                UsageEvent.created_at >= today_start, UsageEvent.created_at < today_end
            )
        )
        revenue_usd = float(revenue_result.scalar() or 0)

        # Query 5: Payments received
        # fx_rate_subquery() returns the FX rate in effect at each payment's
        # created_at, matching the approach used across admin.py analytics.
        # For currencies not in the table (e.g. already-USD rows) it returns
        # NULL; coalesce(..., 1.0) below treats those as a 1:1 rate.
        fx_rate_sq = fx_rate_subquery()

        net_amount_usd = (
            (PaymentEvent.amount - func.coalesce(PaymentEvent.discount_amount, 0))
            / 100.0
            / func.coalesce(fx_rate_sq, 1.0)
        )

        payments_query = select(func.sum(net_amount_usd)).where(
            PaymentEvent.created_at >= today_start,
            PaymentEvent.created_at < today_end,
        )

        payments_result = await session.execute(payments_query)
        payments_received_usd = float(payments_result.scalar() or 0)

        # Query 5b: Coupon discount credits (sum of discount_amount for couponed transactions)
        discount_amount_usd = (
            func.coalesce(PaymentEvent.discount_amount, 0) / 100.0 / func.coalesce(fx_rate_sq, 1.0)
        )

        coupon_discounts_query = select(func.sum(discount_amount_usd)).where(
            PaymentEvent.created_at >= today_start,
            PaymentEvent.created_at < today_end,
            PaymentEvent.coupon_code.isnot(None),
            PaymentEvent.discount_amount > 0,
        )
        coupon_discounts_usd = float((await session.execute(coupon_discounts_query)).scalar() or 0)

        # Query 6: p50/p95 latency per model type (successful requests only)
        latency_result = await session.execute(
            select(
                Model.model_type,
                func.percentile_cont(0.5).within_group(UsageEvent.latency_ms).label("p50"),
                func.percentile_cont(0.95).within_group(UsageEvent.latency_ms).label("p95"),
                func.count(UsageEvent.id).label("count"),
            )
            .join(Model, UsageEvent.model == Model.model_id)
            .where(
                UsageEvent.created_at >= today_start,
                UsageEvent.created_at < today_end,
                UsageEvent.status == "success",
                UsageEvent.latency_ms.isnot(None),
            )
            .group_by(Model.model_type)
        )
        latency_by_model_type: dict[str, dict] = {
            row.model_type: {"p50": int(row.p50), "p95": int(row.p95), "count": row.count}
            for row in latency_result.all()
            if row.model_type is not None
        }

    return DailySummaryMetrics(
        users_onboarded=users_onboarded,
        unique_active_users=unique_active_users,
        requests_processed=requests_processed,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        pending_requests=pending_requests,
        success_rate=success_rate,
        failure_rate=failure_rate,
        pending_rate=pending_rate,
        revenue_usd=revenue_usd,
        payments_received_usd=payments_received_usd,
        coupon_discounts_usd=coupon_discounts_usd,
        error_code_counts=error_code_counts,
        latency_by_model_type=latency_by_model_type,
        timestamp=datetime.now(UTC),
        start_ist=start_ist,
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.post("/v1/metrics/daily-summary", response_model=DailySummaryMetrics)
async def run_daily_metrics(
    _: None = Depends(verify_webhook_key),
) -> DailySummaryMetrics:
    """
    Fetch daily metrics and send to Slack.
    Triggered by Cloud Scheduler daily at 10 AM UTC.
    """
    logger.info("daily_metrics_started")

    metrics = await _get_daily_metrics()
    logger.info(
        "daily_metrics_aggregated",
        users_onboarded=metrics.users_onboarded,
        requests_processed=metrics.requests_processed,
        success_rate=metrics.success_rate,
        revenue_usd=metrics.revenue_usd,
        payments_received_usd=metrics.payments_received_usd,
    )

    # Build Slack message
    fields = [
        {"label": "Timestamp", "value": metrics.timestamp.isoformat()},
        {"label": "Users Onboarded", "value": str(metrics.users_onboarded)},
        {"label": "Unique Active Users", "value": str(metrics.unique_active_users)},
        {"label": "Requests Processed", "value": str(metrics.requests_processed)},
        {"label": "Successful", "value": f"{metrics.successful_requests} ({metrics.success_rate})"},
        {"label": "Failed", "value": f"{metrics.failed_requests} ({metrics.failure_rate})"},
        {"label": "Pending", "value": f"{metrics.pending_requests} ({metrics.pending_rate})"},
        {"label": "Revenue (USD)", "value": f"${metrics.revenue_usd:.4f}"},
        {"label": "Payments Received (USD)", "value": f"${metrics.payments_received_usd:.4f}"},
        {"label": "Coupon Credits Given (USD)", "value": f"${metrics.coupon_discounts_usd:.4f}"},
    ]
    for model_type, stats in sorted(metrics.latency_by_model_type.items()):
        fields.append(
            {
                "label": f"Latency — {model_type.upper()}",
                "value": f"p50: {stats['p50']}ms | p95: {stats['p95']}ms | n={stats['count']}",
            }
        )

    # Optional message: low success rate warning + error code breakdown
    message_parts: list[str] = []

    if metrics.requests_processed > 0 and metrics.success_rate:
        try:
            success_pct = float(metrics.success_rate.rstrip("%"))
            if success_pct < 95:
                message_parts.append(
                    f"⚠️ Success rate is {metrics.success_rate} — lower than expected"
                )
        except (ValueError, AttributeError):
            pass

    if metrics.error_code_counts:
        lines = ["*Error codes:*"]
        for code, count in metrics.error_code_counts.items():
            lines.append(f"• `{code}` — {count}×")
        message_parts.append("\n".join(lines))

    message = "\n\n".join(message_parts) if message_parts else None

    await send_slack_alert(
        title=f"Daily Metrics — {metrics.start_ist.strftime('%Y-%m-%d')} (8AM–8AM IST)",
        fields=fields,
        message=message,
        notify_here=False,  # informational, not actionable
    )

    logger.info("daily_metrics_completed", metrics=metrics.model_dump())

    return metrics
