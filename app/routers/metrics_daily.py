"""
Daily Metrics Summary — POST /v1/metrics/daily-summary

Aggregates daily business metrics (users onboarded, requests processed,
success/failure rates, revenue, and payments received) and sends to Slack.
Intended to be triggered by Cloud Scheduler daily at 8 AM UTC.

Auth: WEBHOOK_API_KEY bearer token (same as /v1/model-health/run).

Cloud Scheduler config:
    Schedule:  0 8 * * *
    URL:       POST https://<routersvc-url>/v1/metrics/daily-summary
    Header:    Authorization: Bearer <WEBHOOK_API_KEY>
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, case

from app.auth.dependencies import verify_webhook_key
from app.db.engine import get_session_factory
from app.db.models import PaymentEvent, User, UsageEvent, CurrencyConversionRate
from app.notifications.slack import send_slack_alert

logger = structlog.get_logger()
router = APIRouter(tags=["metrics"])
IST_OFFSET = timedelta(hours=5, minutes=30)

# ── Response schema ───────────────────────────────────────────────────────────

class DailySummaryMetrics(BaseModel):
    users_onboarded: int
    requests_processed: int
    successful_requests: int
    failed_requests: int
    pending_requests: int
    success_rate: str          # e.g., "98.5%"
    failure_rate: str
    pending_rate: str
    revenue_usd: float
    payments_received_usd: float
    timestamp: datetime
    start_ist: datetime        # Start of the 22:00-22:00 IST window


# ── Internals ─────────────────────────────────────────────────────────────────

async def _get_daily_metrics() -> DailySummaryMetrics:
    """Fetch all daily metrics from database.

    Returns aggregated counts and rates for the current UTC day.
    Never raises; returns zeros if no data found.
    """
    now_utc = datetime.now(UTC)
    now_ist = now_utc + IST_OFFSET

    # Set boundary at 22:00 (10 PM IST)
    if now_ist >= now_ist.replace(hour=22, minute=0, second=0, microsecond=0):
        start_ist = now_ist.replace(hour=22, minute=0, second=0, microsecond=0)
    else:
        start_ist = (now_ist - timedelta(days=1)).replace(hour=22, minute=0, second=0, microsecond=0)

    end_ist = start_ist + timedelta(days=1)

    # Convert back to UTC for DB queries
    today_start = start_ist - IST_OFFSET
    today_end = end_ist - IST_OFFSET

    async with get_session_factory()() as session:
        # Query 1: Users onboarded today
        users_result = await session.execute(
            select(func.count(User.id)).where(
                User.created_at >= today_start,
                User.created_at < today_end
            )
        )
        users_onboarded = users_result.scalar() or 0

        # Query 2: Requests and success/failure rates
        usage_result = await session.execute(
            select(
                func.count(UsageEvent.id).label("total"),
                func.count(UsageEvent.id).filter(UsageEvent.status == "success").label("success"),
                func.count(UsageEvent.id).filter(UsageEvent.status == "error").label("failed"),
                func.count(UsageEvent.id).filter(UsageEvent.status == "pending").label("pending"),
            ).where(
                UsageEvent.created_at >= today_start,
                UsageEvent.created_at < today_end
            )
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

        # Query 3: Revenue (all requests)
        revenue_result = await session.execute(
            select(func.sum(UsageEvent.cost_usd)).where(
                UsageEvent.created_at >= today_start,
                UsageEvent.created_at < today_end
            )
        )
        revenue_usd = float(revenue_result.scalar() or 0)

        # Query 4: Payments received
        # Get latest INR rate for conversion
        inr_rate_result = await session.execute(
            select(CurrencyConversionRate.total_rate)
            .where(CurrencyConversionRate.currency == "INR")
            .order_by(CurrencyConversionRate.created_at.desc())
            .limit(1)
        )
        inr_rate = float(inr_rate_result.scalar() or 83.0)

        payments_result = await session.execute(
            select(
                func.sum(
                    case(
                        (PaymentEvent.currency == "INR", (PaymentEvent.amount - func.coalesce(PaymentEvent.discount_amount, 0)) / inr_rate),
                        else_=PaymentEvent.amount - func.coalesce(PaymentEvent.discount_amount, 0)
                    )
                )
            ).where(
                PaymentEvent.created_at >= today_start,
                PaymentEvent.created_at < today_end
            )
        )
        payments_received_usd = float(payments_result.scalar() or 0)/100

    return DailySummaryMetrics(
        users_onboarded=users_onboarded,
        requests_processed=requests_processed,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        pending_requests=pending_requests,
        success_rate=success_rate,
        failure_rate=failure_rate,
        pending_rate=pending_rate,
        revenue_usd=revenue_usd,
        payments_received_usd=payments_received_usd,
        timestamp=now_utc,
        start_ist=start_ist,
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/v1/metrics/daily-summary", response_model=DailySummaryMetrics)
async def run_daily_metrics(
    _: None = Depends(verify_webhook_key),
) -> DailySummaryMetrics:
    """
    Fetch daily metrics and send to Slack.
    Triggered by Cloud Scheduler daily at 8 AM UTC.
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
        {"label": "Requests Processed", "value": str(metrics.requests_processed)},
        {"label": "Successful", "value": f"{metrics.successful_requests} ({metrics.success_rate})"},
        {"label": "Failed", "value": f"{metrics.failed_requests} ({metrics.failure_rate})"},
        {"label": "Pending", "value": f"{metrics.pending_requests} ({metrics.pending_rate})"},
        {"label": "Revenue (USD)", "value": f"${metrics.revenue_usd:.4f}"},
        {"label": "Payments Received (USD)", "value": f"${metrics.payments_received_usd:.4f}"},
    ]

    # Optional warning if success rate is low
    message = None
    if metrics.requests_processed > 0 and metrics.success_rate:
        try:
            success_pct = float(metrics.success_rate.rstrip("%"))
            if success_pct < 95:
                message = f"⚠️ Success rate is {metrics.success_rate} — lower than expected"
        except (ValueError, AttributeError):
            pass

    await send_slack_alert(
        title=f"Daily Metrics — {metrics.start_ist.strftime('%Y-%m-%d')} (10PM–10PM IST)",
        fields=fields,
        message=message,
        notify_here=False,  # informational, not actionable
    )

    logger.info("daily_metrics_completed", metrics=metrics.model_dump())

    return metrics
