#!/usr/bin/env python3
"""
Seed Bedrock model metadata and pricing into the RouterSVC database.

Usage
-----
  # Seed all 34 models (chat + embedding) — skips models already in DB:
  python scripts/seed_bedrock_models.py

  # Overwrite existing pricing rows too:
  python scripts/seed_bedrock_models.py --overwrite

  # Only seed models that appear in a passed-models file from test_bedrock_models.py:
  python scripts/seed_bedrock_models.py --passed-only scripts/outputs/bedrock_passed_*.txt

Requires: DATABASE_URL in environment (or .env file in project root).
          pip install asyncpg sqlalchemy python-dotenv
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# Model catalogue: canonical_id → (bedrock_model_id, context_length, is_embed)
# context_length=0 means unknown.  is_embed=True = embedding model (not chat).
# ---------------------------------------------------------------------------

_CATALOGUE: dict[str, tuple[str, int, bool]] = {
    # ── AI21 ──────────────────────────────────────────────────────────────────
    "ai21/jamba-instruct-v1":                   ("us.ai21.jamba-instruct-v1:0",             256_000, False),
    "ai21/j2-mid-v1":                           ("us.ai21.j2-mid-v1",                         8_192, False),
    "ai21/j2-ultra-v1":                         ("us.ai21.j2-ultra-v1",                       8_192, False),
    # ── Amazon Nova / Titan ───────────────────────────────────────────────────
    "amazon/nova-premier-v1":                   ("us.amazon.nova-premier-v1:0",             300_000, False),
    "amazon/titan-tg1-large":                   ("us.amazon.titan-tg1-large",                 8_192, False),
    "amazon/titan-embed-text-v1":               ("us.amazon.titan-embed-text-v1",             8_192, True),
    "amazon/titan-embed-text-v2":               ("us.amazon.titan-embed-text-v2:0",           8_192, True),
    "amazon/titan-embed-image-v1":              ("us.amazon.titan-embed-image-v1",                0, True),
    # ── Anthropic ─────────────────────────────────────────────────────────────
    "anthropic/claude-3-5-haiku-20241022-v1":   ("us.anthropic.claude-3-5-haiku-20241022-v1:0", 200_000, False),
    # ── Cohere ────────────────────────────────────────────────────────────────
    "cohere/command-r-v1":                      ("us.cohere.command-r-v1:0",                128_000, False),
    "cohere/command-r-plus-v1":                 ("us.cohere.command-r-plus-v1:0",           128_000, False),
    "cohere/embed-english-v3":                  ("us.cohere.embed-english-v3",                    0, True),
    "cohere/embed-multilingual-v3":             ("us.cohere.embed-multilingual-v3",               0, True),
    "cohere/embed-v4":                          ("us.cohere.embed-v4:0",                          0, True),
    # ── DeepSeek ──────────────────────────────────────────────────────────────
    "deepseek/v3-v1":                           ("us.deepseek.v3-v1:0",                     128_000, False),
    # ── Google ────────────────────────────────────────────────────────────────
    "google/gemma-3-27b-it":                    ("us.google.gemma-3-27b-it",                128_000, False),
    # ── Meta Llama 2 ──────────────────────────────────────────────────────────
    "meta/llama2-13b-v1":                       ("us.meta.llama2-13b-v1",                     4_096, False),
    "meta/llama2-70b-v1":                       ("us.meta.llama2-70b-v1",                     4_096, False),
    "meta/llama2-13b-chat-v1":                  ("us.meta.llama2-13b-chat-v1",                4_096, False),
    "meta/llama2-70b-chat-v1":                  ("us.meta.llama2-70b-chat-v1",                4_096, False),
    # ── Meta Llama 3.x ────────────────────────────────────────────────────────
    "meta/llama3-1-405b-instruct-v1":           ("us.meta.llama3-1-405b-instruct-v1:0",     128_000, False),
    "meta/llama3-2-1b-instruct-v1":             ("us.meta.llama3-2-1b-instruct-v1:0",       128_000, False),
    "meta/llama3-2-3b-instruct-v1":             ("us.meta.llama3-2-3b-instruct-v1:0",       128_000, False),
    "meta/llama3-2-11b-instruct-v1":            ("us.meta.llama3-2-11b-instruct-v1:0",      128_000, False),
    "meta/llama3-2-90b-instruct-v1":            ("us.meta.llama3-2-90b-instruct-v1:0",      128_000, False),
    # ── Mistral ───────────────────────────────────────────────────────────────
    "mistral/mistral-large-2407-v1":            ("us.mistral.mistral-large-2407-v1:0",       32_000, False),
    # ── NVIDIA ────────────────────────────────────────────────────────────────
    "nvidia/nemotron-nano-9b-v2":               ("us.nvidia.nemotron-nano-9b-v2",            128_000, False),
    "nvidia/nemotron-nano-12b-v2":              ("us.nvidia.nemotron-nano-12b-v2",           128_000, False),
    # ── OpenAI Safeguard ──────────────────────────────────────────────────────
    "openai/gpt-oss-safeguard-20b":             ("us.openai.gpt-oss-safeguard-20b",               0, False),
    "openai/gpt-oss-safeguard-120b":            ("us.openai.gpt-oss-safeguard-120b",              0, False),
    # ── Qwen ──────────────────────────────────────────────────────────────────
    "qwen/qwen3-235b-a22b-2507-v1":             ("us.qwen.qwen3-235b-a22b-2507-v1:0",       128_000, False),
    "qwen/qwen3-coder-480b-a35b-v1":            ("us.qwen.qwen3-coder-480b-a35b-v1:0",      128_000, False),
    "qwen/qwen3-coder-next":                    ("us.qwen.qwen3-coder-next",                       0, False),
    "qwen/qwen3-vl-235b-a22b":                  ("us.qwen.qwen3-vl-235b-a22b",                    0, False),
}

# Upstream Bedrock pricing (USD per 1 000 tokens).
# Retail prices are initialised to the same value — apply markup afterwards via
# PATCH /admin/model-prices if desired.
_PRICING: dict[str, tuple[float, float]] = {
    "ai21/jamba-instruct-v1":                   (0.0005,   0.0007),
    "ai21/j2-mid-v1":                           (0.0125,   0.0125),
    "ai21/j2-ultra-v1":                         (0.0188,   0.0188),
    "amazon/nova-premier-v1":                   (0.0025,   0.0125),
    "amazon/titan-tg1-large":                   (0.0003,   0.0004),
    "amazon/titan-embed-text-v1":               (0.0001,   0.0),
    "amazon/titan-embed-text-v2":               (0.00002,  0.0),
    "amazon/titan-embed-image-v1":              (0.00008,  0.0),
    "anthropic/claude-3-5-haiku-20241022-v1":   (0.0008,   0.004),
    "cohere/command-r-v1":                      (0.0005,   0.0015),
    "cohere/command-r-plus-v1":                 (0.003,    0.015),
    "cohere/embed-english-v3":                  (0.0001,   0.0),
    "cohere/embed-multilingual-v3":             (0.0001,   0.0),
    "cohere/embed-v4":                          (0.0001,   0.0),
    "deepseek/v3-v1":                           (0.00062,  0.00185),
    "google/gemma-3-27b-it":                    (0.00023,  0.00038),
    "meta/llama2-13b-v1":                       (0.00075,  0.001),
    "meta/llama2-70b-v1":                       (0.00195,  0.00256),
    "meta/llama2-13b-chat-v1":                  (0.00075,  0.001),
    "meta/llama2-70b-chat-v1":                  (0.00195,  0.00256),
    "meta/llama3-1-405b-instruct-v1":           (0.00532,  0.016),
    "meta/llama3-2-1b-instruct-v1":             (0.0001,   0.0001),
    "meta/llama3-2-3b-instruct-v1":             (0.00015,  0.00015),
    "meta/llama3-2-11b-instruct-v1":            (0.00035,  0.00035),
    "meta/llama3-2-90b-instruct-v1":            (0.002,    0.002),
    "mistral/mistral-large-2407-v1":            (0.003,    0.009),
    "nvidia/nemotron-nano-9b-v2":               (0.00006,  0.00023),
    "nvidia/nemotron-nano-12b-v2":              (0.0002,   0.0006),
    "openai/gpt-oss-safeguard-20b":             (0.00007,  0.0002),
    "openai/gpt-oss-safeguard-120b":            (0.00015,  0.0006),
    "qwen/qwen3-235b-a22b-2507-v1":             (0.00023,  0.00091),
    "qwen/qwen3-coder-480b-a35b-v1":            (0.0005,   0.00216),
    "qwen/qwen3-coder-next":                    (0.0005,   0.0012),
    "qwen/qwen3-vl-235b-a22b":                  (0.00053,  0.00266),
}


def _display_name(model_id: str) -> str:
    """Generate a human-readable name from the canonical model_id slug."""
    _, slug = model_id.split("/", 1)
    return slug.replace("-", " ").replace("_", " ").replace(".", " ").title()


def _load_passed_ids(path: str) -> set[str]:
    """Read a bedrock_passed_*.txt file and return the set of model_ids."""
    p = Path(path)
    if not p.exists():
        print(f"ERROR: passed-only file not found: {path}", file=sys.stderr)
        sys.exit(1)
    ids = {line.strip() for line in p.read_text().splitlines() if line.strip()}
    print(f"  Loaded {len(ids)} passed model IDs from {path}")
    return ids


async def _seed(database_url: str, overwrite: bool, passed_ids: set[str] | None) -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(database_url, echo=False)

    candidates = {
        mid: info
        for mid, info in _CATALOGUE.items()
        if passed_ids is None or mid in passed_ids
    }

    seeded_models = 0
    seeded_prices = 0
    skipped = 0

    async with engine.begin() as conn:
        for model_id, (provider_model_id, ctx, is_embed) in sorted(candidates.items()):
            inp, out = _PRICING.get(model_id, (0.0, 0.0))
            name  = _display_name(model_id)
            brand = model_id.split("/")[0]
            ctx_val = ctx if ctx else None
            description = "Embedding model — use InvokeModel API, not Converse." if is_embed else None
            # Embedding models are disabled by default since this adapter doesn't support them.
            is_enabled = not is_embed

            # ── models table ─────────────────────────────────────────────────
            if overwrite:
                await conn.execute(text("""
                    INSERT INTO models (model_id, name, brand, context_length, description, is_enabled)
                    VALUES (:mid, :name, :brand, :ctx, :desc, :enabled)
                    ON CONFLICT (model_id) DO UPDATE SET
                        name          = EXCLUDED.name,
                        brand         = EXCLUDED.brand,
                        context_length = EXCLUDED.context_length,
                        description   = EXCLUDED.description
                """), {"mid": model_id, "name": name, "brand": brand, "ctx": ctx_val,
                       "desc": description, "enabled": is_enabled})
            else:
                await conn.execute(text("""
                    INSERT INTO models (model_id, name, brand, context_length, description, is_enabled)
                    VALUES (:mid, :name, :brand, :ctx, :desc, :enabled)
                    ON CONFLICT (model_id) DO NOTHING
                """), {"mid": model_id, "name": name, "brand": brand, "ctx": ctx_val,
                       "desc": description, "enabled": is_enabled})
            seeded_models += 1

            # ── model_prices table ────────────────────────────────────────────
            existing = await conn.execute(
                text("SELECT 1 FROM model_prices WHERE model_id = :mid AND provider = 'bedrock'"),
                {"mid": model_id},
            )
            row_exists = existing.scalar_one_or_none() is not None

            if row_exists and not overwrite:
                skipped += 1
                continue

            if overwrite and row_exists:
                await conn.execute(text("""
                    UPDATE model_prices SET
                        provider_model_id              = :pmid,
                        prompt_usd_per_1k              = :inp,
                        completion_usd_per_1k          = :out,
                        upstream_prompt_usd_per_1k     = :inp,
                        upstream_completion_usd_per_1k = :out,
                        is_free                        = false
                    WHERE model_id = :mid AND provider = 'bedrock'
                """), {"pmid": provider_model_id, "inp": Decimal(str(inp)),
                       "out": Decimal(str(out)), "mid": model_id})
            else:
                await conn.execute(text("""
                    INSERT INTO model_prices
                        (model_id, provider, provider_model_id, is_default,
                         prompt_usd_per_1k, completion_usd_per_1k, is_free,
                         upstream_prompt_usd_per_1k, upstream_completion_usd_per_1k)
                    VALUES (:mid, 'bedrock', :pmid, true,
                            :inp, :out, false, :inp, :out)
                    ON CONFLICT (model_id, provider) DO NOTHING
                """), {"mid": model_id, "pmid": provider_model_id,
                       "inp": Decimal(str(inp)), "out": Decimal(str(out))})
            seeded_prices += 1

    await engine.dispose()
    print(f"\n  Done. models: {seeded_models}  model_prices: {seeded_prices}  skipped: {skipped}")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Seed Bedrock model metadata and pricing into RouterSVC DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--overwrite", action="store_true",
        help="Update existing rows instead of skipping them.",
    )
    p.add_argument(
        "--passed-only", metavar="FILE",
        help="Only seed models listed in a bedrock_passed_*.txt file from test_bedrock_models.py.",
    )
    p.add_argument(
        "--database-url", default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL (or $DATABASE_URL).",
    )
    return p.parse_args()


async def _main(args: argparse.Namespace) -> int:
    # Try to load .env from project root if python-dotenv is available.
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")
    except ImportError:
        pass

    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: --database-url or $DATABASE_URL is required.", file=sys.stderr)
        return 1

    # SQLAlchemy async requires asyncpg driver prefix.
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)

    passed_ids: set[str] | None = None
    if args.passed_only:
        passed_ids = _load_passed_ids(args.passed_only)

    total = len(_CATALOGUE) if passed_ids is None else len(passed_ids & _CATALOGUE.keys())
    missing = (passed_ids or set()) - _CATALOGUE.keys()
    if missing:
        print(f"  WARNING: {len(missing)} passed IDs not found in catalogue: {sorted(missing)}")

    print(f"\n  Seeding {total} models into DB  (overwrite={args.overwrite})")

    try:
        await _seed(database_url, args.overwrite, passed_ids)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main(_parse_args())))
