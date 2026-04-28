"""
Balance Reconciliation — POST /internal/reconcile

Compares each user's balance_ledger sum against their user_balances.balance_usd.
Reports any discrepancy and sends a Slack summary.

Intended to be triggered by Cloud Scheduler (e.g. hourly).

Auth: WEBHOOK_API_KEY bearer token.

Cloud Scheduler config:
    Schedule:  0 * * * *
    URL:       POST https://<routersvc-url>/internal/reconcile
    Header:    Authorization: Bearer <WEBHOOK_API_KEY>

Note on legacy data
-------------------
Users with balance history before migration 0040 will show discrepancy equal to
their entire current balance (ledger_net=0, balance>0). This is expected on
first run and can be identified by the absence of any balance_ledger rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.auth.dependencies import verify_webhook_key
from app.db.engine import get_session_factory
from app.db.models import BalanceLedger, UserBalance
from app.notifications.slack import send_slack_alert

logger = structlog.get_logger()
router = APIRouter(tags=["internal"])


class ReconcileResult(BaseModel):
    checked: int
    drifted: int
    total_discrepancy_usd: str


@router.post("/internal/reconcile", response_model=ReconcileResult)
async def run_reconciliation(
    _: None = Depends(verify_webhook_key),
) -> ReconcileResult:
    """
    Scan all users and compare ledger sum against stored balance.

    Processes users in batches of 100 to avoid long-held transactions.
    Sends a Slack summary regardless of outcome.
    """
    PAGE_SIZE = 100
    DRIFT_THRESHOLD = Decimal("0.000001")

    checked = 0
    drifted_users: list[dict] = []
    offset = 0

    async with get_session_factory()() as session:
        # Count total users first for pagination.
        count_result = await session.execute(
            select(func.count()).select_from(UserBalance)
        )
        total_users = count_result.scalar_one()

        while offset < total_users:
            balance_rows = (
                await session.execute(
                    select(UserBalance)
                    .order_by(UserBalance.user_id)
                    .offset(offset)
                    .limit(PAGE_SIZE)
                )
            ).scalars().all()

            if not balance_rows:
                break

            user_ids = [row.user_id for row in balance_rows]

            # Single aggregate query for all users in this batch.
            agg_rows = (
                await session.execute(
                    select(
                        BalanceLedger.user_id,
                        func.coalesce(
                            func.sum(BalanceLedger.amount_usd).filter(
                                BalanceLedger.txn_type == "credit"
                            ),
                            Decimal("0"),
                        ).label("total_credits"),
                        func.coalesce(
                            func.sum(BalanceLedger.amount_usd).filter(
                                BalanceLedger.txn_type == "debit"
                            ),
                            Decimal("0"),
                        ).label("total_debits"),
                    )
                    .where(BalanceLedger.user_id.in_(user_ids))
                    .group_by(BalanceLedger.user_id)
                )
            ).all()

            ledger_by_user = {
                row.user_id: (row.total_credits, row.total_debits)
                for row in agg_rows
            }

            for balance_row in balance_rows:
                uid = balance_row.user_id
                credits, debits = ledger_by_user.get(uid, (Decimal("0"), Decimal("0")))
                ledger_net = credits - debits
                discrepancy = ledger_net - balance_row.balance_usd

                if abs(discrepancy) >= DRIFT_THRESHOLD:
                    drifted_users.append({
                        "user_id": uid,
                        "balance_usd": balance_row.balance_usd,
                        "ledger_net": ledger_net,
                        "discrepancy_usd": discrepancy,
                    })
                    logger.error(
                        "balance_reconciliation_drift",
                        user_id=uid,
                        current_balance_usd=str(balance_row.balance_usd),
                        ledger_net=str(ledger_net),
                        discrepancy_usd=str(discrepancy),
                    )

            checked += len(balance_rows)
            offset += PAGE_SIZE

    total_discrepancy = sum(abs(u["discrepancy_usd"]) for u in drifted_users)

    await _send_slack_summary(
        checked=checked,
        drifted_users=drifted_users,
        total_discrepancy=total_discrepancy,
    )

    return ReconcileResult(
        checked=checked,
        drifted=len(drifted_users),
        total_discrepancy_usd=str(total_discrepancy),
    )


async def _send_slack_summary(
    *,
    checked: int,
    drifted_users: list[dict],
    total_discrepancy: Decimal,
) -> None:
    drifted = len(drifted_users)
    run_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    if drifted == 0:
        title = f"✅ Balance Reconciliation — All {checked} users balanced"
    else:
        title = f"⚠️ Balance Reconciliation — {checked} checked, {drifted} drifted"

    fields = [
        {"label": "Users Checked", "value": str(checked)},
        {"label": "Users with Drift", "value": str(drifted)},
        {"label": "Total Discrepancy", "value": f"${total_discrepancy:,.6f}"},
        {"label": "Run At", "value": run_at},
    ]

    message: str | None = None
    if drifted_users:
        lines = []
        for u in drifted_users[:20]:  # cap at 20 to keep Slack message readable
            lines.append(
                f"• `{u['user_id']}` — discrepancy: `${u['discrepancy_usd']:+.6f}` "
                f"(ledger_net: `${u['ledger_net']:.6f}`, balance: `${u['balance_usd']:.6f}`)"
            )
        if len(drifted_users) > 20:
            lines.append(f"_…and {len(drifted_users) - 20} more_")
        message = "\n".join(lines)

    await send_slack_alert(
        title=title,
        fields=fields,
        message=message,
        notify_here=drifted > 0,
    )
