"""
backfill_usage_user_id.py — populate usage_events.user_id from api_keys.owner.

Joins usage_events.key_id → api_keys.id to resolve the owner (Supabase user ID)
and writes it into the new user_id column. Processes rows in batches to avoid
long-running transactions on a large table.

Usage:
    python scripts/backfill_usage_user_id.py [--dry-run] [--batch-size N]

Requires env vars (in .env or exported):
    DATABASE_URL    postgresql+asyncpg://...   (or plain postgresql://...)

Options:
    --dry-run       Count affected rows and exit without writing.
    --batch-size N  Rows per UPDATE batch (default: 10000).
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
    """Convert SQLAlchemy-style URL to asyncpg DSN."""
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def main(dry_run: bool, batch_size: int) -> None:
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)

    dsn = _asyncpg_dsn(raw_url)
    conn = await asyncpg.connect(dsn)

    try:
        total_null = await conn.fetchval(
            "SELECT COUNT(*) FROM usage_events WHERE user_id IS NULL"
        )
        print(f"Rows with user_id NULL: {total_null:,}")

        if dry_run or total_null == 0:
            if total_null == 0:
                print("Nothing to backfill.")
            return

        updated_total = 0
        batch_num = 0

        while True:
            batch_num += 1
            # Batch UPDATE: pick up to batch_size rows that still have user_id NULL,
            # join to api_keys to resolve owner, write it back.
            rows = await conn.fetchval(
                """
                WITH batch AS (
                    SELECT id, key_id FROM usage_events
                    WHERE user_id IS NULL
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE usage_events ue
                SET user_id = ak.owner
                FROM batch
                JOIN api_keys ak ON ak.id = batch.key_id
                WHERE ue.id = batch.id
                """,
                batch_size,
            )
            # asyncpg returns the UPDATE count as a string like "UPDATE 9843"
            count = int(str(rows).split()[-1]) if rows else 0
            updated_total += count
            print(f"  Batch {batch_num}: updated {count:,} rows  (total so far: {updated_total:,})")

            if count < batch_size:
                break

        remaining = await conn.fetchval(
            "SELECT COUNT(*) FROM usage_events WHERE user_id IS NULL"
        )
        print(f"\nDone. Updated {updated_total:,} rows. Remaining NULL: {remaining:,}")

    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill usage_events.user_id")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no writes")
    parser.add_argument("--batch-size", type=int, default=10_000, metavar="N")
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, batch_size=args.batch_size))
