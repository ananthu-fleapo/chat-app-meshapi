"""
backfill_users.py — populate the `users` table from api_keys.owner + auth.users in Supabase PG.

Usage:
    python scripts/backfill_users.py [--dry-run] [--missing-only]

Requires env vars (in .env or exported):
    DATABASE_URL        postgresql+asyncpg://...  (read api_keys, write users)
    READONLY_MAIN_PG    postgresql://...          (read auth.users from Supabase PG)

Options:
    --dry-run       Print what would be upserted, don't write to DB.
    --missing-only  Only process owners not already in the users table (default: upsert all).
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import ssl

import asyncpg
from dotenv import load_dotenv

# Load .env from the backend/ directory
load_dotenv(Path(__file__).parent.parent / ".env.prod")


def get_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"ERROR: {name} is not set", file=sys.stderr)
        sys.exit(1)
    return val


def asyncpg_dsn(url: str) -> str:
    """Strip the SQLAlchemy +asyncpg driver prefix so asyncpg can parse the DSN."""
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def main(dry_run: bool, missing_only: bool) -> int:
    database_url = get_env("DATABASE_URL")
    readonly_pg = get_env("READONLY_MAIN_PG")

    # Two separate connections: one to our app DB, one to Supabase PG (readonly)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    app_conn = await asyncpg.connect(asyncpg_dsn(database_url), ssl=ssl_ctx)
    sb_conn = await asyncpg.connect(readonly_pg, ssl=ssl_ctx)

    try:
        # 1. Collect owner IDs to process
        if missing_only:
            rows = await app_conn.fetch(
                """
                SELECT DISTINCT ak.owner
                FROM api_keys ak
                LEFT JOIN users u ON u.id = ak.owner
                WHERE u.id IS NULL
                ORDER BY ak.owner
                """
            )
        else:
            rows = await app_conn.fetch(
                "SELECT DISTINCT owner FROM api_keys ORDER BY owner"
            )

        owners = [r["owner"] for r in rows]
        print(f"Found {len(owners)} distinct owner(s) to process.")

        if not owners:
            print("Nothing to do.")
            return 0

        # 2. Bulk-fetch matching rows from auth.users in Supabase PG
        sb_rows = await sb_conn.fetch(
            """
            SELECT id::text, email, full_name
            FROM public.users
            WHERE id::text = ANY($1::text[])
            """,
            owners,
        )
        sb_by_id = {r["id"]: r for r in sb_rows}
        print(f"Fetched {len(sb_by_id)} matching auth.users record(s) from Supabase PG.")

        # 3. Upsert into users table
        ok = skipped = errors = 0

        for owner_id in owners:
            user = sb_by_id.get(owner_id)

            if user is None:
                print(f"  SKIP  {owner_id}: not found in public.users")
                skipped += 1
                continue

            email: str = user["email"] or ""
            if not email:
                print(f"  SKIP  {owner_id}: no email in auth.users")
                skipped += 1
                continue

            display_name: str | None = user["full_name"] or None

            if dry_run:
                print(f"  DRY   {owner_id}: would upsert email={email!r}" + (f", display_name={display_name!r}" if display_name else ""))
                ok += 1
                continue

            try:
                await app_conn.execute(
                    """
                    INSERT INTO users (id, email, display_name)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (id) DO UPDATE
                        SET email        = EXCLUDED.email,
                            display_name = COALESCE(EXCLUDED.display_name, users.display_name),
                            updated_at   = now()
                    """,
                    owner_id,
                    email,
                    display_name,
                )
                print(f"  OK    {owner_id}: upserted email={email!r}" + (f", display_name={display_name!r}" if display_name else ""))
                ok += 1
            except Exception as exc:
                print(f"  ERROR {owner_id}: {exc}")
                errors += 1

    finally:
        await app_conn.close()
        await sb_conn.close()

    print(
        f"\nDone — ok={ok}, skipped={skipped}, errors={errors}"
        + (" (dry run, no writes)" if dry_run else "")
    )
    return 1 if errors else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill users table from api_keys.owner + Supabase auth.users"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing to DB")
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Only process owners not already present in users table",
    )
    args = parser.parse_args()

    sys.exit(asyncio.run(main(dry_run=args.dry_run, missing_only=args.missing_only)))
