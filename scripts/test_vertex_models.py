#!/usr/bin/env python3
"""
Test Vertex AI models directly using the OpenAI-compatible endpoint.

Usage
-----
  python scripts/test_vertex_models.py \\
      --project-id  my-gcp-project \\
      --sa-json     /path/to/service_account.json \\
      [--location   us-central1] \\
      [--timeout    60] \\
      [--prompt     "Reply with just the word OK"]

Output files (timestamped, never overwritten)
----------------------------------------------
  vertex_results_YYYYMMDD_HHMMSS.json
  vertex_passed_YYYYMMDD_HHMMSS.txt

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

import httpx

_OUTPUTS_DIR = Path(__file__).parent / "outputs"
_OUTPUTS_DIR.mkdir(exist_ok=True)

# ── Model registry (canonical → vertex model ID, context length) ─────────────

MODELS: dict[str, tuple[str, int]] = {
    "anthropic/claude-opus-4-6":    ("claude-opus-4-6",              200_000),
    "anthropic/claude-sonnet-4-6":  ("claude-sonnet-4-6",            200_000),
    "anthropic/claude-haiku-4-5":   ("claude-haiku-4-5@20251001",    200_000),
    "anthropic/claude-sonnet-4-5":  ("claude-sonnet-4-5@20250929",   200_000),
    "anthropic/claude-opus-4-5":    ("claude-opus-4-5@20251101",     200_000),
    "anthropic/claude-opus-4-1":    ("claude-opus-4-1@20250805",     200_000),
    "anthropic/claude-sonnet-4":    ("claude-sonnet-4@20250514",     200_000),
    "anthropic/claude-opus-4":      ("claude-opus-4@20250514",       200_000),
    "anthropic/claude-3-haiku":     ("claude-3-haiku@20240307",      200_000),
    "google/gemini-3-1-pro":        ("gemini-3-1-pro",             1_000_000),
    "google/gemini-3-flash":        ("gemini-3-flash",             1_000_000),
    "google/gemini-3-1-flash-lite": ("gemini-3-1-flash-lite",      1_000_000),
    "google/gemini-2-5-pro":        ("gemini-2-5-pro",             1_000_000),
    "google/gemini-2-5-flash":      ("gemini-2-5-flash",           1_000_000),
    "google/gemini-2-5-flash-lite": ("gemini-2-5-flash-lite",      1_000_000),
    "google/gemini-2-0-flash":      ("gemini-2-0-flash",           1_000_000),
}

# ── ANSI colours ──────────────────────────────────────────────────────────────

_IS_TTY = sys.stdout.isatty()


def _c(code: str, t: str) -> str:
    return f"\033[{code}m{t}\033[0m" if _IS_TTY else t


def green(t: str)   -> str: return _c("92", t)
def red(t: str)     -> str: return _c("91", t)
def yellow(t: str)  -> str: return _c("93", t)
def cyan(t: str)    -> str: return _c("96", t)
def bold(t: str)    -> str: return _c("1",  t)
def dim(t: str)     -> str: return _c("2",  t)
def magenta(t: str) -> str: return _c("95", t)


# ── Data ──────────────────────────────────────────────────────────────────────

Status = Literal["pass", "fail", "timeout"]


@dataclass
class ModelResult:
    model_id:         str
    vertex_model_id:  str
    status:           Status
    http_status:      int | None  = None
    latency_ms:       int | None  = None
    response_preview: str | None  = None
    raw_body_preview: str | None  = None
    error:            str | None  = None


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_bearer_token(sa_json_path: str) -> str:
    """Obtain a short-lived Google OAuth2 Bearer token from a service account JSON file."""
    try:
        from google.auth.transport.requests import Request as GoogleRequest  # type: ignore[import]
        from google.oauth2 import service_account  # type: ignore[import]
    except ImportError:
        print(red("google-auth is required: pip install google-auth"))
        sys.exit(1)

    with open(sa_json_path) as f:
        sa_info = json.load(f)

    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(GoogleRequest())
    return creds.token  # type: ignore[return-value]


# ── Single model test ─────────────────────────────────────────────────────────

async def _test_model(
    canonical_id: str,
    vertex_model_id: str,
    endpoint_url: str,
    bearer_token: str,
    prompt: str,
    timeout: float,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    idx: int,
    total: int,
    print_lock: asyncio.Lock,
) -> ModelResult:
    async with sem:
        t0 = time.monotonic()
        try:
            resp = await client.post(
                endpoint_url,
                headers={"Authorization": f"Bearer {bearer_token}"},
                json={
                    "model":    vertex_model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 32,
                },
                timeout=httpx.Timeout(timeout),
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            raw_body   = resp.text

            if resp.status_code == 200:
                try:
                    body = resp.json()
                except Exception:
                    result = ModelResult(
                        model_id=canonical_id, vertex_model_id=vertex_model_id,
                        status="fail", http_status=200, latency_ms=latency_ms,
                        raw_body_preview=raw_body[:200], error="Invalid JSON response",
                    )
                else:
                    text = (
                        (body.get("choices") or [{}])[0]
                        .get("message", {})
                        .get("content") or ""
                    ).strip()
                    if text:
                        result = ModelResult(
                            model_id=canonical_id, vertex_model_id=vertex_model_id,
                            status="pass", http_status=200, latency_ms=latency_ms,
                            response_preview=text[:120],
                        )
                    else:
                        result = ModelResult(
                            model_id=canonical_id, vertex_model_id=vertex_model_id,
                            status="fail", http_status=200, latency_ms=latency_ms,
                            raw_body_preview=raw_body[:300], error="Empty response content",
                        )
            else:
                try:
                    msg = resp.json().get("error", {}).get("message", raw_body)[:200]
                except Exception:
                    msg = raw_body[:200]
                result = ModelResult(
                    model_id=canonical_id, vertex_model_id=vertex_model_id,
                    status="fail", http_status=resp.status_code, latency_ms=latency_ms,
                    error=f"HTTP {resp.status_code}: {msg}",
                )

        except httpx.TimeoutException:
            latency_ms = int((time.monotonic() - t0) * 1000)
            result = ModelResult(
                model_id=canonical_id, vertex_model_id=vertex_model_id,
                status="timeout", latency_ms=latency_ms,
                error=f"Timed out after {timeout:.0f}s",
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.monotonic() - t0) * 1000)
            result = ModelResult(
                model_id=canonical_id, vertex_model_id=vertex_model_id,
                status="fail", latency_ms=latency_ms, error=str(exc),
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
    http_col = cyan(f"[{r.http_status}]") if r.http_status else dim("[---]")

    if r.status == "pass" and r.response_preview:
        note = f"  {dim(repr(r.response_preview[:60]))}"
    elif r.status == "fail" and r.raw_body_preview:
        note = f"  {dim('body: ' + r.raw_body_preview[:80])}"
    elif r.error:
        note = f"  {dim(r.error[:90])}"
    else:
        note = ""

    print(
        f"[{idx:>{width}}/{total}] {icon} "
        f"{r.model_id:<50} {dim(f'({r.vertex_model_id})'):<35} "
        f"{http_col} {cyan(f'{latency:>8}')}"
        f"{note}"
    )


def _print_summary(results: list[ModelResult], elapsed: float) -> None:
    passed   = [r for r in results if r.status == "pass"]
    failed   = [r for r in results if r.status in ("fail", "timeout")]
    latencies = [r.latency_ms for r in passed if r.latency_ms]

    bar = "━" * 78
    print(f"\n{bar}")
    print(bold("Vertex AI Results"))
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
            print(f"  {green('✓')} {r.model_id:<50} {cyan(lat):>10}  {dim(repr(r.response_preview or ''))}")
        print(f"\n  {bold('Fastest')}  {by_lat[0].model_id}  {cyan(str(by_lat[0].latency_ms) + 'ms')}")
        print(f"  {bold('Slowest')}  {by_lat[-1].model_id}  {cyan(str(by_lat[-1].latency_ms) + 'ms')}")

    if failed:
        print(f"\n{bold(red('Failed models'))}  ({len(failed)})")
        for r in sorted(failed, key=lambda r: r.model_id):
            icon = _STATUS_ICON.get(r.status, lambda: "?")()
            print(f"  {icon} {r.model_id:<50}  {dim(r.error or '')}")

    print(bar)


# ── SQL output ────────────────────────────────────────────────────────────────

def _model_display_name(canonical_id: str) -> str:
    parts = canonical_id.split("/", 1)
    slug  = parts[1] if len(parts) == 2 else parts[0]
    return slug.replace("-", " ").replace("_", " ").title()


def _print_sql(results: list[ModelResult]) -> None:
    passed = [r for r in results if r.status == "pass"]
    if not passed:
        print("\n-- No passed models — no SQL generated.")
        return

    print("\n" + "─" * 78)
    print(bold("SQL INSERT statements for passed models (provider=vertex)"))
    print("─" * 78)
    print("\nBEGIN;\n")

    for r in sorted(passed, key=lambda r: r.model_id):
        ctx   = MODELS[r.model_id][1]
        name  = _model_display_name(r.model_id).replace("'", "''")
        mid   = r.model_id.replace("'", "''")
        pmid  = r.vertex_model_id.replace("'", "''")
        print(f"-- {r.model_id}  →  {r.vertex_model_id}")
        print(f"INSERT INTO models (model_id, name, context_length, description, is_enabled)")
        print(f"VALUES ('{mid}', '{name}', {ctx}, NULL, true);")
        print(f"INSERT INTO model_prices (model_id, provider, provider_model_id, is_default, prompt_usd_per_1k, completion_usd_per_1k, is_free)")
        print(f"VALUES ('{mid}', 'vertex', '{pmid}', true, 0, 0, false);")
        print()

    print("COMMIT;")


# ── File output ───────────────────────────────────────────────────────────────

def _write_outputs(results: list[ModelResult], ts: str) -> tuple[str, str]:
    json_path   = str(_OUTPUTS_DIR / f"vertex_results_{ts}.json")
    passed_path = str(_OUTPUTS_DIR / f"vertex_passed_{ts}.txt")

    report = {
        "run_at":   datetime.now(timezone.utc).isoformat(),
        "provider": "vertex",
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
        description="Test Vertex AI models directly and output SQL INSERTs for passed ones.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--project-id", default=os.environ.get("VERTEX_PROJECT_ID"),
        help="GCP project ID (or $VERTEX_PROJECT_ID).")
    p.add_argument("--location", default=os.environ.get("VERTEX_LOCATION", "us-central1"),
        help="Vertex AI region (default: us-central1).")
    p.add_argument("--sa-json", default=os.environ.get("VERTEX_SA_JSON"),
        help="Path to service account JSON file (or $VERTEX_SA_JSON).")
    p.add_argument("--timeout", type=float, default=60.0,
        help="Per-model timeout in seconds (default: 60).")
    p.add_argument("--concurrency", type=int, default=3,
        help="Parallel requests (default: 3).")
    p.add_argument("--prompt", default="Reply with just the word OK and nothing else.",
        help="Test prompt sent to every model.")
    return p.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

async def _main(args: argparse.Namespace) -> int:
    if not args.project_id:
        print(red("Error: --project-id is required (or set $VERTEX_PROJECT_ID)"))
        return 1
    if not args.sa_json:
        print(red("Error: --sa-json is required (or set $VERTEX_SA_JSON)"))
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print(bold("\n  Vertex AI Model Tester"))
    print(f"  Project:      {args.project_id}")
    print(f"  Location:     {args.location}")
    print(f"  Concurrency:  {args.concurrency}")
    print(f"  Timeout:      {args.timeout}s / model")
    print(f"  Models:       {len(MODELS)}")
    print()

    # Auth
    print("Obtaining Google OAuth2 Bearer token... ", end="", flush=True)
    try:
        bearer_token = _get_bearer_token(args.sa_json)
        print(green("OK"))
    except Exception as exc:
        print(red(f"FAILED: {exc}"))
        return 1

    endpoint_url = (
        f"https://{args.location}-aiplatform.googleapis.com/v1beta1"
        f"/projects/{args.project_id}/locations/{args.location}"
        f"/endpoints/openapi/chat/completions"
    )
    print(f"  Endpoint:     {endpoint_url}")
    print()
    print("─" * 78)

    sem        = asyncio.Semaphore(args.concurrency)
    print_lock = asyncio.Lock()
    t_start    = time.monotonic()

    model_items = list(MODELS.items())

    async with httpx.AsyncClient() as client:
        tasks = [
            _test_model(
                canonical_id=canonical_id,
                vertex_model_id=vertex_id,
                endpoint_url=endpoint_url,
                bearer_token=bearer_token,
                prompt=args.prompt,
                timeout=args.timeout,
                client=client,
                sem=sem,
                idx=i + 1,
                total=len(model_items),
                print_lock=print_lock,
            )
            for i, (canonical_id, (vertex_id, _)) in enumerate(model_items)
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
