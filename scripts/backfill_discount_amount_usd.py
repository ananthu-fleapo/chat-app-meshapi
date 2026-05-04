"""
backfill_discount_amount_usd.py — populate payment_events.discount_amount_usd for old rows.

Strategy:
  USD payments: discount_amount is already in cents — copy as-is.
  INR payments: discount_amount is in paisa — look up the most recent
                currency_conversion_rates row whose created_at <= payment created_at
                and compute ROUND(discount_amount / total_rate).
                Dividing paisa by the INR/USD rate yields USD cents directly
                (both scales are ×100, so they cancel):
                  85000 paisa / 85 (INR/USD) = 1000 USD cents = $10.00

Only rows where:
  - discount_amount IS NOT NULL and discount_amount > 0
  - discount_amount_usd IS NULL  (not yet backfilled)

are processed. Rows with no discount are skipped.
Rows where no FX rate entry exists for the payment's created_at are left NULL
and reported at the end.

Usage:
    python scripts/backfill_discount_amount_usd.py [--dry-run] [--batch-size N]

Requires:
    DATABASE_URL  postgresql+asyncpg://...  (in .env.prod or exported)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.prod")


def _asyncpg_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def main(dry_run: bool, batch_size: int) -> None:
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)

    conn = await asyncpg.connect(_asyncpg_dsn(raw_url))

    try:
        total_null = await conn.fetchval(
            """
            SELECT COUNT(*) FROM payment_events
            WHERE discount_amount IS NOT NULL
              AND discount_amount > 0
              AND discount_amount_usd IS NULL
            """
        )
        print(f"Rows to backfill: {total_null:,}")

        # Diagnostics: show currency breakdown and rate availability
        diag_rows = await conn.fetch(
            """
            SELECT
                pe.currency,
                COUNT(*) AS payment_count,
                MIN(pe.created_at) AS earliest_payment,
                MAX(pe.created_at) AS latest_payment,
                (SELECT MIN(ccr.created_at) FROM currency_conversion_rates ccr
                 WHERE UPPER(ccr.currency) = UPPER(pe.currency)) AS earliest_rate,
                (SELECT MAX(ccr.created_at) FROM currency_conversion_rates ccr
                 WHERE UPPER(ccr.currency) = UPPER(pe.currency)) AS latest_rate,
                (SELECT ccr.total_rate FROM currency_conversion_rates ccr
                 WHERE UPPER(ccr.currency) = UPPER(pe.currency)
                 ORDER BY ccr.created_at ASC LIMIT 1) AS earliest_rate_value
            FROM payment_events pe
            WHERE pe.discount_amount IS NOT NULL
              AND pe.discount_amount > 0
              AND pe.discount_amount_usd IS NULL
            GROUP BY pe.currency
            """
        )
        print("\nDiagnostics:")
        for row in diag_rows:
            print(
                f"  currency={row['currency']!r}  payments={row['payment_count']}"
                f"  payment_range=[{row['earliest_payment']} → {row['latest_payment']}]"
                f"  rate_range=[{row['earliest_rate']} → {row['latest_rate']}]"
                f"  earliest_rate_value={row['earliest_rate_value']}"
            )
        print()

        if total_null == 0:
            print("Nothing to backfill.")
            return

        if dry_run:
            print("--dry-run: exiting without writes.")
            return

        updated_total = 0
        batch_num = 0

        while True:
            batch_num += 1

            # USD: discount_amount is already in cents — copy as-is.
            # INR: discount_amount is in paisa. Dividing by the INR/USD rate gives
            #      USD cents directly (×100 scales cancel):
            #      85000 paisa / 85 (INR/USD) = 1000 USD cents = $10.00
            # We intentionally do NOT use the amount_usd/amount ratio because
            # amount_usd is net of GST (credited amount), which would distort the rate.
            status = await conn.execute(
                """
                WITH batch AS (
                    SELECT pe.id,
                           pe.discount_amount,
                           pe.currency,
                           pe.created_at,
                           COALESCE(
                               -- Exact: most recent rate at or before payment time
                               (
                                   SELECT ccr.total_rate
                                   FROM currency_conversion_rates ccr
                                   WHERE UPPER(ccr.currency) = UPPER(pe.currency)
                                     AND ccr.created_at <= pe.created_at
                                   ORDER BY ccr.created_at DESC
                                   LIMIT 1
                               ),
                               -- Fallback: earliest available rate for payments
                               -- that predate the rate table
                               (
                                   SELECT ccr.total_rate
                                   FROM currency_conversion_rates ccr
                                   WHERE UPPER(ccr.currency) = UPPER(pe.currency)
                                   ORDER BY ccr.created_at ASC
                                   LIMIT 1
                               )
                           ) AS fx_rate
                    FROM payment_events pe
                    WHERE pe.discount_amount IS NOT NULL
                      AND pe.discount_amount > 0
                      AND pe.discount_amount_usd IS NULL
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE payment_events pe
                SET discount_amount_usd = CASE
                    WHEN UPPER(batch.currency) = 'USD'
                        THEN batch.discount_amount
                    WHEN batch.fx_rate IS NOT NULL AND batch.fx_rate > 0
                        THEN ROUND(batch.discount_amount::numeric / batch.fx_rate)
                    ELSE NULL
                END
                FROM batch
                WHERE pe.id = batch.id
                  AND (
                      UPPER(batch.currency) = 'USD'
                      OR (batch.fx_rate IS NOT NULL AND batch.fx_rate > 0)
                  )
                """,
                batch_size,
            )
            # conn.execute() returns a command tag string like "UPDATE 21"
            count = int(status.split()[-1])
            updated_total += count

            print(f"  Batch {batch_num}: updated {count:,}  (total so far: {updated_total:,})")

            if count < batch_size:
                break

        remaining = await conn.fetchval(
            """
            SELECT COUNT(*) FROM payment_events
            WHERE discount_amount IS NOT NULL
              AND discount_amount > 0
              AND discount_amount_usd IS NULL
            """
        )
        print(f"\nDone. Updated {updated_total:,} rows.")
        if remaining > 0:
            print(
                f"  {remaining:,} rows still NULL — likely missing FX rate entries."
                " Check currency_conversion_rates for those created_at timestamps."
            )

    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill payment_events.discount_amount_usd")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no writes")
    parser.add_argument("--batch-size", type=int, default=5_000, metavar="N")
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, batch_size=args.batch_size))
