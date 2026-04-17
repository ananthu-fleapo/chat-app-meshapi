#!/usr/bin/env python3
"""
Test AWS Bedrock models directly via the Bedrock Converse API.

Usage
-----
  python scripts/test_bedrock_models.py \\
      --access-key  AKIAIOSFODNN7EXAMPLE \\
      --secret-key  wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \\
      [--region     us-east-1] \\
      [--timeout    60] \\
      [--prompt     "Reply with just the word OK"]

Environment variable fallbacks: $AWS_ACCESS_KEY_ID, $AWS_SECRET_ACCESS_KEY, $AWS_DEFAULT_REGION

Requires: pip install boto3

Output files (timestamped, never overwritten)
----------------------------------------------
  bedrock_results_YYYYMMDD_HHMMSS.json
  bedrock_passed_YYYYMMDD_HHMMSS.txt

SQL INSERT statements for passed models are printed to stdout at the end.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

_OUTPUTS_DIR = Path(__file__).parent / "outputs"
_OUTPUTS_DIR.mkdir(exist_ok=True)

# ── Model registry (canonical → bedrock model ID, context length) ─────────────
#
# Cross-region inference profiles use a region prefix (us. / eu. / ap.).
# Models shown as "Geo cross-region" or "Global cross-region" in the Bedrock
# console quota page must be called with the prefixed inference profile ID.
# On-demand models use the plain anthropic.* ID.
#
# Run with --region us-east-1 (default) for US geo cross-region profiles.

# MODELS: canonical_id → (bedrock_model_id, context_length_tokens)
# Embedding-only models (titan-embed-*, cohere/embed-*) are excluded — they require
# InvokeModel, not Converse, and cannot be tested with this script.
MODELS: dict[str, tuple[str, int]] = {
    # ── Anthropic Claude 4.x ──────────────────────────────────────────────────
    "anthropic/claude-sonnet-4-5":              ("us.anthropic.claude-sonnet-4-5-20250929-v1:0",   200_000),
    "anthropic/claude-opus-4-5":                ("us.anthropic.claude-opus-4-5-20251101-v1:0",     200_000),
    "anthropic/claude-sonnet-4":                ("us.anthropic.claude-sonnet-4-20250514-v1:0",     200_000),
    "anthropic/claude-opus-4-1":                ("us.anthropic.claude-opus-4-1-20250805-v1:0",     200_000),
    "anthropic/claude-haiku-4-5":               ("us.anthropic.claude-haiku-4-5-20251001-v1:0",    200_000),
    # ── Anthropic Claude 3.x ──────────────────────────────────────────────────
    "anthropic/claude-3-haiku":                 ("us.anthropic.claude-3-haiku-20240307-v1:0",      200_000),
    "anthropic/claude-3-5-haiku-20241022-v1":   ("us.anthropic.claude-3-5-haiku-20241022-v1:0",   200_000),
    # ── Amazon Nova / Titan ───────────────────────────────────────────────────
    "amazon/nova-premier-v1":                   ("us.amazon.nova-premier-v1:0",                    300_000),
    "amazon/nova-pro-v1":                       ("us.amazon.nova-pro-v1:0",                        300_000),
    "amazon/nova-lite-v1":                      ("us.amazon.nova-lite-v1:0",                       300_000),
    "amazon/nova-micro-v1":                     ("us.amazon.nova-micro-v1:0",                      128_000),
    "amazon/titan-tg1-large":                   ("us.amazon.titan-tg1-large",                        8_192),
    # ── AI21 ──────────────────────────────────────────────────────────────────
    "ai21/jamba-instruct-v1":                   ("us.ai21.jamba-instruct-v1:0",                   256_000),
    "ai21/j2-mid-v1":                           ("us.ai21.j2-mid-v1",                               8_192),
    "ai21/j2-ultra-v1":                         ("us.ai21.j2-ultra-v1",                             8_192),
    # ── Cohere Command ────────────────────────────────────────────────────────
    "cohere/command-r-v1":                      ("us.cohere.command-r-v1:0",                      128_000),
    "cohere/command-r-plus-v1":                 ("us.cohere.command-r-plus-v1:0",                 128_000),
    # ── DeepSeek ──────────────────────────────────────────────────────────────
    "deepseek/v3-v1":                           ("us.deepseek.v3-v1:0",                           128_000),
    # ── Google ────────────────────────────────────────────────────────────────
    "google/gemma-3-27b-it":                    ("us.google.gemma-3-27b-it",                      128_000),
    # ── Meta Llama 2 ──────────────────────────────────────────────────────────
    "meta/llama2-13b-v1":                       ("us.meta.llama2-13b-v1",                           4_096),
    "meta/llama2-70b-v1":                       ("us.meta.llama2-70b-v1",                           4_096),
    "meta/llama2-13b-chat-v1":                  ("us.meta.llama2-13b-chat-v1",                      4_096),
    "meta/llama2-70b-chat-v1":                  ("us.meta.llama2-70b-chat-v1",                      4_096),
    # ── Meta Llama 3.x ────────────────────────────────────────────────────────
    "meta/llama3-1-405b-instruct-v1":           ("us.meta.llama3-1-405b-instruct-v1:0",           128_000),
    "meta/llama3-2-1b-instruct-v1":             ("us.meta.llama3-2-1b-instruct-v1:0",             128_000),
    "meta/llama3-2-3b-instruct-v1":             ("us.meta.llama3-2-3b-instruct-v1:0",             128_000),
    "meta/llama3-2-11b-instruct-v1":            ("us.meta.llama3-2-11b-instruct-v1:0",            128_000),
    "meta/llama3-2-90b-instruct-v1":            ("us.meta.llama3-2-90b-instruct-v1:0",            128_000),
    # ── Mistral ───────────────────────────────────────────────────────────────
    "mistral/mistral-large-2407-v1":            ("us.mistral.mistral-large-2407-v1:0",             32_000),
    # ── NVIDIA ────────────────────────────────────────────────────────────────
    "nvidia/nemotron-nano-9b-v2":               ("us.nvidia.nemotron-nano-9b-v2",                 128_000),
    "nvidia/nemotron-nano-12b-v2":              ("us.nvidia.nemotron-nano-12b-v2",                128_000),
    # ── OpenAI Safeguard ──────────────────────────────────────────────────────
    "openai/gpt-oss-safeguard-20b":             ("us.openai.gpt-oss-safeguard-20b",                    0),
    "openai/gpt-oss-safeguard-120b":            ("us.openai.gpt-oss-safeguard-120b",                   0),
    # ── Qwen ──────────────────────────────────────────────────────────────────
    "qwen/qwen3-235b-a22b-2507-v1":             ("us.qwen.qwen3-235b-a22b-2507-v1:0",            128_000),
    "qwen/qwen3-coder-480b-a35b-v1":            ("us.qwen.qwen3-coder-480b-a35b-v1:0",           128_000),
    "qwen/qwen3-coder-next":                    ("us.qwen.qwen3-coder-next",                           0),
    "qwen/qwen3-vl-235b-a22b":                  ("us.qwen.qwen3-vl-235b-a22b",                        0),
    # ── Claude 4.x (geo cross-region inference profiles) ─────────────────────
    "anthropic/claude-sonnet-4-5":        ("us.anthropic.claude-sonnet-4-5-20250929-v1:0",   200_000),
    "anthropic/claude-opus-4-5":          ("us.anthropic.claude-opus-4-5-20251101-v1:0",     200_000),
    "anthropic/claude-sonnet-4":          ("us.anthropic.claude-sonnet-4-20250514-v1:0",     200_000),
    "anthropic/claude-opus-4-1":          ("us.anthropic.claude-opus-4-1-20250805-v1:0",     200_000),
    "anthropic/claude-haiku-4-5":         ("us.anthropic.claude-haiku-4-5-20251001-v1:0",    200_000),
    # ── Claude 3.x ────────────────────────────────────────────────────────────
    "anthropic/claude-3-haiku":           ("us.anthropic.claude-3-haiku-20240307-v1:0",      200_000),
    # ── Amazon Nova (cross-region) ────────────────────────────────────────────
    "amazon/nova-lite-v1":                ("us.amazon.nova-lite-v1:0",                       300_000),
    "amazon/nova-micro-v1":               ("us.amazon.nova-micro-v1:0",                      128_000),
    "amazon/nova-pro-v1":                 ("us.amazon.nova-pro-v1:0",                        300_000),
    # ── Removed — confirmed dead as of 2026-04 ────────────────────────────────
    # "anthropic/claude-opus-4":          EOL  — "marked by provider as Legacy"
    # "anthropic/claude-3-7-sonnet":      EOL  — "marked by provider as Legacy"
    # "anthropic/claude-3-5-haiku":       EOL  — "marked by provider as Legacy"
    # "anthropic/claude-3-5-sonnet":      EOL  — ValidationException: invalid model identifier
    # "anthropic/claude-3-5-sonnet-v2":   EOL  — ValidationException: invalid model identifier
    # "anthropic/claude-3-sonnet":        EOL  — "marked by provider as Legacy"
    # "anthropic/claude-instant":         EOL  — "end of its life"
    # "anthropic/claude-v2":              EOL  — "end of its life"
    # ── Not yet on Bedrock ────────────────────────────────────────────────────
    # "anthropic/claude-sonnet-4-6":      ValidationException (20260101 date not live yet)
    # "anthropic/claude-opus-4-6":        ValidationException (20260101 date not live yet)
}

# Upstream pricing from AWS Bedrock (USD per 1 000 tokens).
# Used when generating SQL INSERT statements for the model_prices table.
# Retail prices (prompt_usd_per_1k / completion_usd_per_1k) are set equal to
# upstream here — apply a markup in the DB after validating the models work.
PRICING: dict[str, tuple[float, float]] = {
    # canonical_id: (input_per_1k, output_per_1k)
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
    # Existing models (already in DB — included for completeness)
    "amazon/nova-pro-v1":                       (0.0008,   0.0032),
    "amazon/nova-lite-v1":                      (0.00006,  0.00024),
    "amazon/nova-micro-v1":                     (0.000035, 0.00014),
    "anthropic/claude-sonnet-4-5":              (0.003,    0.015),
    "anthropic/claude-opus-4-5":                (0.015,    0.075),
    "anthropic/claude-sonnet-4":                (0.003,    0.015),
    "anthropic/claude-opus-4-1":                (0.015,    0.075),
    "anthropic/claude-haiku-4-5":               (0.0008,   0.004),
    "anthropic/claude-3-haiku":                 (0.00025,  0.00125),
}

# ── ANSI colours ──────────────────────────────────────────────────────────────

_IS_TTY = sys.stdout.isatty()


def _c(code: str, t: str) -> str:
    return f"\033[{code}m{t}\033[0m" if _IS_TTY else t


def green(t: str)   -> str: return _c("92", t)
def red(t: str)     -> str: return _c("91", t)
def cyan(t: str)    -> str: return _c("96", t)
def bold(t: str)    -> str: return _c("1",  t)
def dim(t: str)     -> str: return _c("2",  t)
def magenta(t: str) -> str: return _c("95", t)


# ── Data ──────────────────────────────────────────────────────────────────────

Status = Literal["pass", "fail", "timeout"]


@dataclass
class ModelResult:
    model_id:        str
    bedrock_model_id: str
    status:          Status
    latency_ms:      int | None  = None
    response_preview: str | None = None
    error:           str | None  = None


# ── Message conversion (OpenAI → Bedrock Converse format) ─────────────────────

def _to_bedrock_messages(prompt: str) -> tuple[list[dict], list[dict]]:
    """Return (bedrock_messages, system_blocks) for a simple user prompt."""
    return (
        [{"role": "user", "content": [{"text": prompt}]}],
        [],  # no system message
    )


# ── Single model test (sync, runs in thread pool) ─────────────────────────────

def _converse_sync(
    bedrock_model_id: str,
    prompt: str,
    access_key: str,
    secret_key: str,
    region: str,
) -> tuple[str, float]:
    """
    Call bedrock:converse synchronously.
    Returns (response_text, latency_s). Raises on any error.
    """
    import boto3  # type: ignore[import]

    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    messages, system_blocks = _to_bedrock_messages(prompt)
    kwargs: dict = {
        "modelId":          bedrock_model_id,
        "messages":         messages,
        "inferenceConfig":  {"maxTokens": 32},
    }
    if system_blocks:
        kwargs["system"] = system_blocks

    t0       = time.monotonic()
    response = client.converse(**kwargs)
    latency  = time.monotonic() - t0

    content = response.get("output", {}).get("message", {}).get("content", [])
    text    = "".join(block.get("text", "") for block in content).strip()
    return text, latency


# ── Async wrapper ─────────────────────────────────────────────────────────────

async def _test_model(
    canonical_id: str,
    bedrock_model_id: str,
    prompt: str,
    timeout: float,
    access_key: str,
    secret_key: str,
    region: str,
    sem: asyncio.Semaphore,
    idx: int,
    total: int,
    print_lock: asyncio.Lock,
) -> ModelResult:
    async with sem:
        t0 = time.monotonic()
        try:
            text, latency = await asyncio.wait_for(
                asyncio.to_thread(
                    _converse_sync,
                    bedrock_model_id, prompt, access_key, secret_key, region,
                ),
                timeout=timeout,
            )
            latency_ms = int(latency * 1000)

            if text:
                result = ModelResult(
                    model_id=canonical_id, bedrock_model_id=bedrock_model_id,
                    status="pass", latency_ms=latency_ms,
                    response_preview=text[:120],
                )
            else:
                result = ModelResult(
                    model_id=canonical_id, bedrock_model_id=bedrock_model_id,
                    status="fail", latency_ms=latency_ms,
                    error="Empty response content",
                )

        except asyncio.TimeoutError:
            latency_ms = int((time.monotonic() - t0) * 1000)
            result = ModelResult(
                model_id=canonical_id, bedrock_model_id=bedrock_model_id,
                status="timeout", latency_ms=latency_ms,
                error=f"Timed out after {timeout:.0f}s",
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.monotonic() - t0) * 1000)
            result = ModelResult(
                model_id=canonical_id, bedrock_model_id=bedrock_model_id,
                status="fail", latency_ms=latency_ms,
                error=str(exc)[:200],
            )

    async with print_lock:
        _print_row(result, idx, total)
    return result


# ── Console output ─────────────────────────────────────────────────────────────

_STATUS_ICON = {
    "pass":    lambda: green("✓"),
    "fail":    lambda: red("✗"),
    "timeout": lambda: magenta("⏱"),
}


def _print_row(r: ModelResult, idx: int, total: int) -> None:
    width   = len(str(total))
    icon    = _STATUS_ICON.get(r.status, lambda: "?")()
    latency = f"{r.latency_ms}ms" if r.latency_ms is not None else "—"

    if r.status == "pass" and r.response_preview:
        note = f"  {dim(repr(r.response_preview[:60]))}"
    elif r.error:
        note = f"  {dim(r.error[:90])}"
    else:
        note = ""

    print(
        f"[{idx:>{width}}/{total}] {icon} "
        f"{r.model_id:<52} {dim(f'({r.bedrock_model_id})'):<45} "
        f"{cyan(f'{latency:>8}')}"
        f"{note}"
    )


def _print_summary(results: list[ModelResult], elapsed: float) -> None:
    passed    = [r for r in results if r.status == "pass"]
    failed    = [r for r in results if r.status != "pass"]
    latencies = [r.latency_ms for r in passed if r.latency_ms]

    bar = "━" * 78
    print(f"\n{bar}")
    print(bold("AWS Bedrock Results"))
    print(bar)
    print(f"  Total:     {bold(str(len(results)))}")
    print(f"  {green('Passed:')}    {bold(green(str(len(passed))))}")
    print(f"  {red('Failed:')}    {bold(red(str(len(failed))))}")
    if latencies:
        print(f"  Latency:   avg {int(sum(latencies)/len(latencies))}ms  "
              f"min {min(latencies)}ms  max {max(latencies)}ms")
    print(f"  Wall time: {elapsed:.1f}s")

    if passed:
        by_lat = sorted(passed, key=lambda r: r.latency_ms or 999_999)
        print(f"\n{bold(green('Passed models'))}  ({len(passed)})")
        for r in sorted(passed, key=lambda r: r.model_id):
            lat = f"{r.latency_ms}ms" if r.latency_ms else "—"
            print(f"  {green('✓')} {r.model_id:<52} {cyan(lat):>10}  {dim(repr(r.response_preview or ''))}")
        print(f"\n  {bold('Fastest')}  {by_lat[0].model_id}  {cyan(str(by_lat[0].latency_ms) + 'ms')}")
        print(f"  {bold('Slowest')}  {by_lat[-1].model_id}  {cyan(str(by_lat[-1].latency_ms) + 'ms')}")

    if failed:
        print(f"\n{bold(red('Failed models'))}  ({len(failed)})")
        for r in sorted(failed, key=lambda r: r.model_id):
            icon = _STATUS_ICON.get(r.status, lambda: "?")()
            print(f"  {icon} {r.model_id:<52}  {dim(r.error or '')}")

    print(bar)


# ── SQL output ────────────────────────────────────────────────────────────────

def _model_display_name(canonical_id: str) -> str:
    parts = canonical_id.split("/", 1)
    slug  = parts[1] if len(parts) == 2 else parts[0]
    return slug.replace("-", " ").replace("_", " ").replace(".", " ").title()


def _print_sql(results: list[ModelResult]) -> None:
    passed = [r for r in results if r.status == "pass"]
    if not passed:
        print("\n-- No passed models — no SQL generated.")
        return

    print("\n" + "─" * 78)
    print(bold("SQL INSERT statements for passed models (provider=bedrock)"))
    print("─" * 78)
    print("-- Retail prices are set equal to upstream costs. Apply markup via PATCH /admin/model-prices.")
    print("\nBEGIN;\n")

    for r in sorted(passed, key=lambda r: r.model_id):
        ctx  = MODELS[r.model_id][1]
        name = _model_display_name(r.model_id).replace("'", "''")
        mid  = r.model_id.replace("'", "''")
        pmid = r.bedrock_model_id.replace("'", "''")
        brand = r.model_id.split("/")[0].replace("'", "''")
        inp, out = PRICING.get(r.model_id, (0.0, 0.0))
        ctx_val  = ctx if ctx else "NULL"

        print(f"-- {r.model_id}  →  {r.bedrock_model_id}  ({inp}/1k in, {out}/1k out)")
        print(f"INSERT INTO models (model_id, name, brand, context_length, description, is_enabled)")
        print(f"  VALUES ('{mid}', '{name}', '{brand}', {ctx_val}, NULL, true)")
        print(f"  ON CONFLICT (model_id) DO NOTHING;")
        print(f"INSERT INTO model_prices")
        print(f"  (model_id, provider, provider_model_id, is_default,")
        print(f"   prompt_usd_per_1k, completion_usd_per_1k, is_free,")
        print(f"   upstream_prompt_usd_per_1k, upstream_completion_usd_per_1k)")
        print(f"  VALUES ('{mid}', 'bedrock', '{pmid}', true,")
        print(f"          {inp}, {out}, false, {inp}, {out})")
        print(f"  ON CONFLICT (model_id, provider) DO UPDATE SET")
        print(f"    provider_model_id = EXCLUDED.provider_model_id,")
        print(f"    upstream_prompt_usd_per_1k = EXCLUDED.upstream_prompt_usd_per_1k,")
        print(f"    upstream_completion_usd_per_1k = EXCLUDED.upstream_completion_usd_per_1k;")
        print()

    print("COMMIT;")


# ── File output ───────────────────────────────────────────────────────────────

def _write_outputs(results: list[ModelResult], ts: str) -> tuple[str, str]:
    json_path   = str(_OUTPUTS_DIR / f"bedrock_results_{ts}.json")
    passed_path = str(_OUTPUTS_DIR / f"bedrock_passed_{ts}.txt")

    report = {
        "run_at":   datetime.now(timezone.utc).isoformat(),
        "provider": "bedrock",
        "total":    len(results),
        "passed":   sum(1 for r in results if r.status == "pass"),
        "failed":   sum(1 for r in results if r.status != "pass"),
        "models":   [asdict(r) for r in sorted(results, key=lambda r: r.model_id)],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    passed_ids = sorted(r.model_id for r in results if r.status == "pass")
    with open(passed_path, "w", encoding="utf-8") as f:
        f.write("\n".join(passed_ids) + ("\n" if passed_ids else ""))

    return json_path, passed_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Test AWS Bedrock models directly and output SQL INSERTs for passed ones.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--access-key", default=os.environ.get("AWS_ACCESS_KEY_ID"),
        help="AWS access key ID (or $AWS_ACCESS_KEY_ID).")
    p.add_argument("--secret-key", default=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        help="AWS secret access key (or $AWS_SECRET_ACCESS_KEY).")
    p.add_argument("--region", default=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        help="AWS region (default: us-east-1).")
    p.add_argument("--timeout", type=float, default=60.0,
        help="Per-model timeout in seconds (default: 60).")
    p.add_argument("--concurrency", type=int, default=3,
        help="Parallel requests (default: 3).")
    p.add_argument("--prompt", default="Reply with just the word OK and nothing else.",
        help="Test prompt sent to every model.")
    return p.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

async def _main(args: argparse.Namespace) -> int:
    if not args.access_key:
        print(red("Error: --access-key is required (or set $AWS_ACCESS_KEY_ID)"))
        return 1
    if not args.secret_key:
        print(red("Error: --secret-key is required (or set $AWS_SECRET_ACCESS_KEY)"))
        return 1

    try:
        import boto3  # noqa: F401
    except ImportError:
        print(red("boto3 is required: pip install boto3"))
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print(bold("\n  AWS Bedrock Model Tester"))
    print(f"  Region:       {args.region}")
    print(f"  Concurrency:  {args.concurrency}")
    print(f"  Timeout:      {args.timeout}s / model")
    print(f"  Models:       {len(MODELS)}")
    print()
    print("─" * 78)

    sem        = asyncio.Semaphore(args.concurrency)
    print_lock = asyncio.Lock()
    t_start    = time.monotonic()

    model_items = list(MODELS.items())

    tasks = [
        _test_model(
            canonical_id=canonical_id,
            bedrock_model_id=bedrock_id,
            prompt=args.prompt,
            timeout=args.timeout,
            access_key=args.access_key,
            secret_key=args.secret_key,
            region=args.region,
            sem=sem,
            idx=i + 1,
            total=len(model_items),
            print_lock=print_lock,
        )
        for i, (canonical_id, (bedrock_id, _)) in enumerate(model_items)
    ]
    results: list[ModelResult] = list(await asyncio.gather(*tasks))

    elapsed = time.monotonic() - t_start

    _print_summary(results, elapsed)
    _print_sql(results)

    json_path, passed_path = _write_outputs(results, ts)
    passed_count = sum(1 for r in results if r.status == "pass")
    print(f"\n  {bold('Full report')} → {json_path}")
    print(f"  {bold('Passed list')} → {passed_path}  ({passed_count} models)\n")

    return 0 if all(r.status == "pass" for r in results) else 1


def main() -> None:
    sys.exit(asyncio.run(_main(_parse_args())))


if __name__ == "__main__":
    main()
