#!/usr/bin/env python3
"""
Test every model registered in RouterSVC by sending a simple chat request
and reporting pass / fail per model.

Usage
-----
  python scripts/test_models.py \\
      --api-key    rsk_your_routersvc_key \\
      [--base-url  http://localhost:8000] \\
      [--concurrency 3]          # parallel requests     (default: 3)
      [--rate-limit  15]         # max requests / minute (default: 15)
      [--timeout     45]         # per-model seconds     (default: 45)
      [--retries     2]          # retries on 429        (default: 2)
      [--retry-wait  65]         # seconds to wait on 429 (default: 65)
      [--free-only]              # only free-tier models
      [--filter      anthropic]  # model ID substring filter
      [--prompt      "Say OK"]   # override test prompt

Output files (never overwritten — timestamped)
----------------------------------------------
  results_YYYYMMDD_HHMMSS.json   full report
  passed_YYYYMMDD_HHMMSS.txt     one passing model ID per line

Exit code: 0 = all passed, 1 = any failure.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx

# All output files go here, relative to the repo root (or script location)
_OUTPUTS_DIR = Path(__file__).parent / "outputs"
_OUTPUTS_DIR.mkdir(exist_ok=True)

# ── ANSI ──────────────────────────────────────────────────────────────────────

_IS_TTY = sys.stdout.isatty()


def _c(code: str, t: str) -> str:
    return f"\033[{code}m{t}\033[0m" if _IS_TTY else t


def green(t: str)  -> str: return _c("92", t)
def red(t: str)    -> str: return _c("91", t)
def yellow(t: str) -> str: return _c("93", t)
def cyan(t: str)   -> str: return _c("96", t)
def bold(t: str)   -> str: return _c("1",  t)
def dim(t: str)    -> str: return _c("2",  t)
def magenta(t: str)-> str: return _c("95", t)


# ── Data ──────────────────────────────────────────────────────────────────────

Status = Literal["pass", "fail", "rate_limited", "timeout"]


@dataclass
class ModelResult:
    model_id:         str
    status:           Status
    http_status:      int | None    = None
    latency_ms:       int | None    = None
    response_preview: str | None    = None   # first 120 chars of reply text
    raw_body_preview: str | None    = None   # raw JSON snippet when reply is empty
    error:            str | None    = None
    attempts:         int           = 1      # how many attempts were made


# ── Fetch model list ──────────────────────────────────────────────────────────

async def _fetch_models(
    base_url: str,
    api_key: str,
    client: httpx.AsyncClient,
    free_only: bool,
    paid_only: bool,
    filter_str: str,
) -> list[dict]:
    """Fetch enabled models from our own /v1/models endpoint."""
    resp = await client.get(
        f"{base_url}/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    models: list[dict] = resp.json()

    if free_only:
        models = [m for m in models if m.get("is_free")]
    elif paid_only:
        models = [m for m in models if not m.get("is_free")]

    if filter_str:
        models = [m for m in models if filter_str.lower() in m.get("id", "").lower()]

    return models


# ── Rate limiter (token-bucket, 1 token = 1 request) ─────────────────────────

class _RateLimiter:
    """
    Simple async token-bucket: allows at most `rpm` requests per 60 s window.
    Each call to acquire() blocks until a slot is available.
    """
    def __init__(self, rpm: int) -> None:
        self._interval = 60.0 / rpm      # seconds between tokens
        self._last     = 0.0
        self._lock     = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now  = time.monotonic()
            wait = self._last + self._interval - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()


# ── Single-attempt request ────────────────────────────────────────────────────

async def _attempt(
    model_id: str,
    base_url: str,
    api_key: str,
    prompt: str,
    timeout: float,
    client: httpx.AsyncClient,
) -> ModelResult:
    t0 = time.monotonic()
    try:
        resp = await client.post(
            f"{base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model":    model_id,
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
                return ModelResult(
                    model_id=model_id, status="fail",
                    http_status=200, latency_ms=latency_ms,
                    raw_body_preview=raw_body[:200],
                    error="Response is not valid JSON",
                )

            text = (
                (body.get("choices") or [{}])[0]
                .get("message", {})
                .get("content") or ""
            ).strip()

            if text:
                return ModelResult(
                    model_id=model_id, status="pass",
                    http_status=200, latency_ms=latency_ms,
                    response_preview=text[:120],
                )
            else:
                # 200 but empty/null content — capture raw body for diagnosis
                return ModelResult(
                    model_id=model_id, status="fail",
                    http_status=200, latency_ms=latency_ms,
                    raw_body_preview=raw_body[:300],
                    error="Empty response content",
                )

        elif resp.status_code == 429:
            try:
                msg = resp.json().get("error", {}).get("message", raw_body)[:200]
            except Exception:
                msg = raw_body[:200]
            return ModelResult(
                model_id=model_id, status="rate_limited",
                http_status=429, latency_ms=latency_ms,
                error=msg,
            )

        else:
            try:
                msg = resp.json().get("error", {}).get("message", raw_body)[:200]
            except Exception:
                msg = raw_body[:200]
            return ModelResult(
                model_id=model_id, status="fail",
                http_status=resp.status_code, latency_ms=latency_ms,
                error=f"HTTP {resp.status_code}: {msg}",
            )

    except httpx.TimeoutException:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return ModelResult(
            model_id=model_id, status="timeout",
            latency_ms=latency_ms,
            error=f"Timed out after {timeout:.0f}s",
        )
    except httpx.ConnectError as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return ModelResult(
            model_id=model_id, status="fail",
            latency_ms=latency_ms,
            error=f"Connection error: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.monotonic() - t0) * 1000)
        return ModelResult(
            model_id=model_id, status="fail",
            latency_ms=latency_ms,
            error=str(exc),
        )


# ── Test one model (with retries on 429) ──────────────────────────────────────

async def _test_model(
    model: dict,
    base_url: str,
    api_key: str,
    prompt: str,
    timeout: float,
    retries: int,
    retry_wait: float,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    rate_limiter: _RateLimiter,
    idx: int,
    total: int,
    print_lock: asyncio.Lock,
) -> ModelResult:
    model_id: str = model["id"]
    attempts = 0

    async with sem:
        for attempt in range(retries + 1):
            await rate_limiter.acquire()
            attempts += 1
            result = await _attempt(model_id, base_url, api_key, prompt, timeout, client)

            if result.status != "rate_limited" or attempt == retries:
                break

            # 429 — wait and retry
            async with print_lock:
                print(
                    f"  {yellow('⟳')} {model_id}  "
                    f"{yellow('rate limited')} — "
                    f"waiting {retry_wait:.0f}s (attempt {attempt + 1}/{retries + 1})"
                )
            await asyncio.sleep(retry_wait)

    result.attempts = attempts
    async with print_lock:
        _print_row(result, idx, total)

    return result


# ── Console output ─────────────────────────────────────────────────────────────

_STATUS_ICON = {
    "pass":         lambda: green("✓"),
    "fail":         lambda: red("✗"),
    "rate_limited": lambda: yellow("⚡"),
    "timeout":      lambda: magenta("⏱"),
}


def _print_row(r: ModelResult, idx: int, total: int) -> None:
    width    = len(str(total))
    icon     = _STATUS_ICON.get(r.status, lambda: "?")()
    latency  = f"{r.latency_ms}ms" if r.latency_ms is not None else "—"
    http_col = cyan(f"[{r.http_status}]") if r.http_status else dim("[---]")

    # Annotation: show response text for passes, error for failures
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
        f"{r.model_id:<55} {http_col} {cyan(f'{latency:>8}')}"
        f"{note}"
    )


def _print_summary(results: list[ModelResult], elapsed: float) -> None:
    passed       = [r for r in results if r.status == "pass"]
    failed       = [r for r in results if r.status == "fail"]
    rate_limited = [r for r in results if r.status == "rate_limited"]
    timed_out    = [r for r in results if r.status == "timeout"]

    latencies = [r.latency_ms for r in passed if r.latency_ms is not None]
    avg_ms    = int(sum(latencies) / len(latencies)) if latencies else 0
    min_ms    = min(latencies) if latencies else 0
    max_ms    = max(latencies) if latencies else 0

    bar = "━" * 78
    print(f"\n{bar}")
    print(bold("Results"))
    print(bar)
    print(f"  Total:         {bold(str(len(results)))}")
    print(f"  {green('Passed:')}        {bold(green(str(len(passed))))}")
    print(f"  {red('Failed:')}        {bold(red(str(len(failed))))}")
    if rate_limited:
        print(f"  {yellow('Rate limited:')} {bold(yellow(str(len(rate_limited))))}  (exhausted retries)")
    if timed_out:
        print(f"  {magenta('Timed out:')}    {bold(magenta(str(len(timed_out))))}")
    if latencies:
        print(f"  Latency:       avg {avg_ms}ms  min {min_ms}ms  max {max_ms}ms")
    print(f"  Wall time:     {elapsed:.1f}s")

    # ── Passed models ──────────────────────────────────────────────────────────
    if passed:
        by_lat = sorted(passed, key=lambda r: r.latency_ms or 999_999)
        print(f"\n{bold(green('Passed models'))}  ({len(passed)})")
        for r in sorted(passed, key=lambda r: r.model_id):
            lat = f"{r.latency_ms}ms" if r.latency_ms else "—"
            print(f"  {green('✓')} {r.model_id:<55} {cyan(lat):>10}  {dim(repr(r.response_preview or ''))}")
        print(f"\n  {bold('Fastest')}  {by_lat[0].model_id}  {cyan(str(by_lat[0].latency_ms) + 'ms')}")
        print(f"  {bold('Slowest')}  {by_lat[-1].model_id}  {cyan(str(by_lat[-1].latency_ms) + 'ms')}")

    # ── Failed models ──────────────────────────────────────────────────────────
    all_failed = failed + rate_limited + timed_out
    if all_failed:
        print(f"\n{bold(red('Failed / blocked models'))}  ({len(all_failed)})")
        for r in sorted(all_failed, key=lambda r: r.model_id):
            icon = _STATUS_ICON.get(r.status, lambda: "?")()
            http = f"[{r.http_status}]" if r.http_status else "[---]"
            print(f"  {icon} {r.model_id:<55} {http}  {dim(r.error or '')}")

    print(bar)


# ── File output ───────────────────────────────────────────────────────────────

def _make_stem(base: str, ts: str) -> str:
    """Insert timestamp before .json extension: results.json → results_20260402_143022.json"""
    if base.endswith(".json"):
        return base[:-5] + f"_{ts}.json"
    return f"{base}_{ts}.json"


def _write_json(
    results: list[ModelResult],
    args: argparse.Namespace,
    elapsed: float,
    path: str,
) -> None:
    passed = sum(1 for r in results if r.status == "pass")
    report = {
        "run_at":       datetime.now(timezone.utc).isoformat(),
        "base_url":     args.base_url,
        "concurrency":  args.concurrency,
        "rate_limit_rpm": args.rate_limit,
        "timeout_s":    args.timeout,
        "retries":      args.retries,
        "retry_wait_s": args.retry_wait,
        "prompt":       args.prompt,
        "free_only":    args.free_only,
        "filter":       args.filter,
        "wall_time_s":  round(elapsed, 2),
        "total":        len(results),
        "passed":       passed,
        "failed":       len(results) - passed,
        "pass_rate":    round(passed / len(results) * 100, 1) if results else 0,
        "models": [asdict(r) for r in sorted(results, key=lambda r: r.model_id)],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def _write_passed(results: list[ModelResult], path: str) -> None:
    passed_ids = sorted(r.model_id for r in results if r.status == "pass")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(passed_ids) + ("\n" if passed_ids else ""))


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Test all OpenRouter models through RouterSVC.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--api-key",  required=True,
        help="RouterSVC API key (rsk_...) for both model list and inference requests.")
    p.add_argument("--base-url", default="http://localhost:8000",
        help="RouterSVC base URL (default: http://localhost:8000).")
    p.add_argument("--concurrency", type=int, default=3,
        help="Parallel requests in flight (default: 3).")
    p.add_argument("--rate-limit",  type=int, default=15,
        help="Max requests per minute across all workers (default: 15).")
    p.add_argument("--timeout",     type=float, default=45.0,
        help="Per-model timeout seconds (default: 45).")
    p.add_argument("--retries",     type=int, default=2,
        help="Retries on 429 rate-limit response (default: 2).")
    p.add_argument("--retry-wait",  type=float, default=65.0,
        help="Seconds to wait before each 429 retry (default: 65).")
    p.add_argument("--prompt", default="Reply with just the word OK and nothing else.",
        help="Test prompt sent to every model.")
    p.add_argument("--free-only", action="store_true",
        help="Only test free-tier models (prompt + completion = $0).")
    p.add_argument("--paid-only", action="store_true",
        help="Only test paid models (prompt or completion > $0).")
    p.add_argument("--filter", default="",
        help="Only test models whose ID contains this string (case-insensitive).")
    p.add_argument("--output", default="results.json",
        help="Base name for the JSON report (timestamp appended, default: results.json).")
    return p.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

async def _main(args: argparse.Namespace) -> int:
    ts         = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path   = str(_OUTPUTS_DIR / _make_stem(args.output, ts))
    passed_path = str(_OUTPUTS_DIR / f"passed_{ts}.txt")

    print(bold("\n  RouterSVC Model Tester"))
    print(f"  Base URL:     {args.base_url}  (models fetched from /v1/models)")
    print(f"  Concurrency:  {args.concurrency}")
    print(f"  Rate limit:   {args.rate_limit} req/min  ({60/args.rate_limit:.1f}s between requests)")
    print(f"  Timeout:      {args.timeout}s / model")
    print(f"  Retries:      {args.retries} × on 429, wait {args.retry_wait}s each")
    if args.free_only:
        print(f"  {yellow('Mode:         free models only')}")
    elif args.paid_only:
        print(f"  {yellow('Mode:         paid models only')}")
    if args.filter:
        print(f"  Filter:       {args.filter!r}")
    print(f"  Output:       {json_path}  +  {passed_path}")
    print()

    async with httpx.AsyncClient() as client:

        # 1. Fetch model list
        print(f"Fetching model list from {args.base_url}/v1/models... ", end="", flush=True)
        if args.free_only and args.paid_only:
            print(red("Error: --free-only and --paid-only are mutually exclusive."))
            return 1

        try:
            models = await _fetch_models(args.base_url, args.api_key, client, args.free_only, args.paid_only, args.filter)
        except httpx.HTTPStatusError as exc:
            print(red(f"FAILED (HTTP {exc.response.status_code})"))
            print(f"  {exc.response.text[:300]}")
            return 1
        except Exception as exc:  # noqa: BLE001
            print(red(f"FAILED: {exc}"))
            return 1

        if not models:
            print(yellow("0 models matched — nothing to test."))
            return 0

        print(green(f"{len(models)} models found"))
        print()
        print("─" * 78)

        # 2. Run tests
        sem          = asyncio.Semaphore(args.concurrency)
        rate_limiter = _RateLimiter(args.rate_limit)
        print_lock   = asyncio.Lock()
        t_start      = time.monotonic()

        tasks = [
            _test_model(
                model=model,
                base_url=args.base_url,
                api_key=args.api_key,
                prompt=args.prompt,
                timeout=args.timeout,
                retries=args.retries,
                retry_wait=args.retry_wait,
                client=client,
                sem=sem,
                rate_limiter=rate_limiter,
                idx=i + 1,
                total=len(models),
                print_lock=print_lock,
            )
            for i, model in enumerate(models)
        ]

        results: list[ModelResult] = list(await asyncio.gather(*tasks))

    elapsed = time.monotonic() - t_start

    # 3. Summary
    _print_summary(results, elapsed)

    # 4. Write files
    _write_json(results, args, elapsed, json_path)
    _write_passed(results, passed_path)

    passed_count = sum(1 for r in results if r.status == "pass")
    print(f"\n  {bold('Full report')} → {json_path}")
    print(f"  {bold('Passed list')} → {passed_path}  ({passed_count} models)\n")

    return 0 if all(r.status == "pass" for r in results) else 1


def main() -> None:
    sys.exit(asyncio.run(_main(_parse_args())))


if __name__ == "__main__":
    main()
