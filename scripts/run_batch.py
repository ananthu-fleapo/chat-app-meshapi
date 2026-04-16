#!/usr/bin/env python3
"""
Run the full Batch API lifecycle through MeshAPI.

Steps
-----
  1. Submit requests (JSON array) to POST /v1/files
  2. Create a batch job
  3. Poll until completed / failed / cancelled
  4. Download and save the output JSONL
  5. Optionally delete input + output files from the provider

Usage
-----
  python scripts/run_batch.py \\
      --api-key   rsk_your_meshapi_key \\
      [--base-url http://localhost:8000] \\
      [--input    path/to/requests.json]   # JSON array; omit to use built-in sample \\
      [--model    openai/gpt-4o-mini] \\
      [--poll-interval 10] \\
      [--timeout  3600] \\
      [--no-cleanup]

Input file format (JSON array, not JSONL)
-----------------------------------------
  [
    {
      "custom_id": "req-1",
      "body": {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100
      }
    }
  ]

  `method` and `url` default to "POST" / "/v1/chat/completions" if omitted.

Output
------
  scripts/outputs/batch_results_YYYYMMDD_HHMMSS.jsonl   raw output from provider
  scripts/outputs/batch_summary_YYYYMMDD_HHMMSS.json    run metadata

Exit code: 0 = batch completed, 1 = failed / cancelled / timeout.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

_OUTPUTS_DIR = Path(__file__).parent / "outputs"
_OUTPUTS_DIR.mkdir(exist_ok=True)

# ── ANSI colours ─────────────────────────────────────────────────────────────

_IS_TTY = sys.stdout.isatty()


def _c(code: str, t: str) -> str:
    return f"\033[{code}m{t}\033[0m" if _IS_TTY else t


def green(t: str)   -> str: return _c("92", t)
def red(t: str)     -> str: return _c("91", t)
def yellow(t: str)  -> str: return _c("93", t)
def cyan(t: str)    -> str: return _c("96", t)
def bold(t: str)    -> str: return _c("1",  t)
def dim(t: str)     -> str: return _c("2",  t)


# ── Sample requests ───────────────────────────────────────────────────────────

def _sample_requests(model: str) -> list[dict]:
    return [
        {
            "custom_id": "req-1",
            "body": {
                "model": model,
                "messages": [{"role": "user", "content": "Summarize the French Revolution in 2 sentences."}],
                "max_tokens": 200,
            },
        },
        {
            "custom_id": "req-2",
            "body": {
                "model": model,
                "messages": [{"role": "user", "content": "What is the capital of Japan?"}],
                "max_tokens": 50,
            },
        },
        {
            "custom_id": "req-3",
            "body": {
                "model": model,
                "messages": [{"role": "user", "content": "Write a haiku about rain."}],
                "max_tokens": 100,
            },
        },
    ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _print_step(n: int, label: str) -> None:
    print(f"\n{bold(f'[{n}]')} {label}")


def _die(msg: str) -> None:
    print(red(f"\nERROR: {msg}"), file=sys.stderr)
    sys.exit(1)


# ── API calls ─────────────────────────────────────────────────────────────────

def upload_file(client: httpx.Client, requests: list[dict]) -> str:
    _print_step(1, f"Uploading {len(requests)} request(s) …")
    resp = client.post(
        "/v1/files",
        json={"purpose": "batch", "requests": requests},
    )
    if resp.status_code >= 400:
        _die(f"File upload failed ({resp.status_code}): {resp.text[:300]}")
    file_obj = resp.json()
    file_id = file_obj["id"]
    print(f"  {green('✓')} file_id = {bold(file_id)}  ({file_obj.get('bytes', '?')} bytes)")
    return file_id


def create_batch(client: httpx.Client, file_id: str) -> str:
    _print_step(2, "Creating batch job …")
    resp = client.post(
        "/v1/batches",
        json={
            "input_file_id": file_id,
            "endpoint": "/v1/chat/completions",
            "completion_window": "24h",
        },
    )
    if resp.status_code >= 400:
        _die(f"Batch creation failed ({resp.status_code}): {resp.text[:300]}")
    batch = resp.json()
    batch_id = batch["id"]
    print(f"  {green('✓')} batch_id = {bold(batch_id)}  status = {yellow(batch['status'])}")
    return batch_id


_STATUS_COLOUR = {
    "validating":  yellow,
    "in_progress": cyan,
    "finalizing":  cyan,
    "completed":   green,
    "failed":      red,
    "cancelled":   red,
    "cancelling":  yellow,
    "expired":     red,
}


def poll_batch(
    client: httpx.Client,
    batch_id: str,
    poll_interval: int,
    timeout: int,
) -> dict:
    _print_step(3, f"Polling every {poll_interval}s (timeout {timeout}s) …")
    deadline = time.monotonic() + timeout
    last_status = ""

    while time.monotonic() < deadline:
        resp = client.get(f"/v1/batches/{batch_id}")
        if resp.status_code >= 400:
            _die(f"Poll failed ({resp.status_code}): {resp.text[:300]}")
        batch = resp.json()
        status = batch["status"]
        counts = batch.get("request_counts") or {}
        colour = _STATUS_COLOUR.get(status, dim)

        if status != last_status:
            print(f"  status → {colour(status)}", end="")
            last_status = status
        else:
            print(".", end="", flush=True)

        if status in ("completed", "failed", "cancelled", "expired"):
            total     = counts.get("total", "?")
            completed = counts.get("completed", "?")
            failed    = counts.get("failed", "?")
            print(f"\n  requests: total={total}  completed={completed}  failed={failed}")
            return batch

        time.sleep(poll_interval)

    _die(f"Timed out after {timeout}s — batch still in progress. batch_id={batch_id}")


def download_results(client: httpx.Client, output_file_id: str, ts: str) -> Path:
    _print_step(4, f"Downloading results (file_id={output_file_id}) …")
    resp = client.get(f"/v1/files/{output_file_id}/content")
    if resp.status_code >= 400:
        _die(f"Download failed ({resp.status_code}): {resp.text[:300]}")
    out_path = _OUTPUTS_DIR / f"batch_results_{ts}.jsonl"
    out_path.write_bytes(resp.content)
    lines = resp.content.count(b"\n")
    print(f"  {green('✓')} saved {cyan(str(out_path))}  ({lines} results)")
    return out_path


def delete_file(client: httpx.Client, file_id: str, label: str) -> None:
    resp = client.delete(f"/v1/files/{file_id}")
    if resp.status_code >= 400:
        print(yellow(f"  warn: could not delete {label} file {file_id} ({resp.status_code})"))
    else:
        print(f"  {dim(f'deleted {label} file {file_id}')}")


def print_results(results_path: Path) -> None:
    _print_step(5, "Result preview")
    lines = results_path.read_text().strip().splitlines()
    for raw in lines:
        try:
            obj = json.loads(raw)
            cid = obj.get("custom_id", "?")
            response = obj.get("response") or {}
            body = response.get("body") or {}
            choices = body.get("choices") or []
            content = (choices[0].get("message") or {}).get("content", "").strip()[:120] if choices else ""
            status_code = response.get("status_code", "?")
            colour = green if str(status_code) == "200" else red
            print(f"  {bold(cid):12}  [{colour(str(status_code))}]  {dim(content)}")
        except Exception:
            print(f"  {dim(raw[:120])}")


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run MeshAPI Batch API end-to-end")
    p.add_argument("--api-key",       required=True,                   help="MeshAPI key (rsk_...)")
    p.add_argument("--base-url",      default="http://localhost:8000",  help="MeshAPI base URL")
    p.add_argument("--input",         default=None,                    help="Path to JSON array of requests (omit to use sample)")
    p.add_argument("--model",         default="openai/gpt-4o-mini",    help="Model for sample requests (ignored when --input is set)")
    p.add_argument("--poll-interval", type=int, default=10,            help="Seconds between status polls (default: 10)")
    p.add_argument("--timeout",       type=int, default=3600,          help="Max seconds to wait for completion (default: 3600)")
    p.add_argument("--no-cleanup",    action="store_true",             help="Keep input/output files on provider after completion")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    ts = _ts()

    # ── Resolve requests ──────────────────────────────────────────────────────
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            _die(f"Input file not found: {input_path}")
        try:
            requests = json.loads(input_path.read_text())
            if not isinstance(requests, list):
                _die("Input file must be a JSON array.")
        except json.JSONDecodeError as e:
            _die(f"Invalid JSON in input file: {e}")
        print(f"{dim('Loaded input:')} {cyan(str(input_path))}  ({len(requests)} requests)")
    else:
        requests = _sample_requests(args.model)
        print(f"{dim('Using built-in sample:')} {len(requests)} requests  model={cyan(args.model)}")

    # ── HTTP client ───────────────────────────────────────────────────────────
    client = httpx.Client(
        base_url=args.base_url.rstrip("/"),
        headers={"Authorization": f"Bearer {args.api_key}"},
        timeout=httpx.Timeout(60.0),
    )

    input_file_id: str | None = None
    output_file_id: str | None = None
    results_path: Path | None = None
    exit_code = 0

    try:
        # Step 1 — upload
        input_file_id = upload_file(client, requests)

        # Step 2 — create batch
        batch_id = create_batch(client, input_file_id)

        # Step 3 — poll
        batch = poll_batch(client, batch_id, args.poll_interval, args.timeout)

        if batch["status"] != "completed":
            print(red(f"\nBatch ended with status: {batch['status']}"))
            if batch.get("errors"):
                print(red(f"Errors: {json.dumps(batch['errors'], indent=2)}"))
            exit_code = 1
        else:
            # Step 4 — download
            output_file_id = batch.get("output_file_id")
            if output_file_id:
                results_path = download_results(client, output_file_id, ts)
            else:
                print(yellow("  No output_file_id on completed batch (all requests may have failed)"))
                exit_code = 1

            # Step 5 — preview
            if results_path:
                print_results(results_path)

        # Step 6 — save summary
        summary_path = _OUTPUTS_DIR / f"batch_summary_{ts}.json"
        summary_path.write_text(json.dumps({
            "ts": ts,
            "base_url": args.base_url,
            "batch_id": batch_id,
            "input_file_id": input_file_id,
            "output_file_id": output_file_id,
            "status": batch["status"],
            "request_counts": batch.get("request_counts"),
            "results_file": str(results_path) if results_path else None,
        }, indent=2))
        print(f"\n{dim('Summary saved:')} {cyan(str(summary_path))}")

    finally:
        # Cleanup
        if not args.no_cleanup:
            print(f"\n{bold('[7]')} Cleaning up files …")
            if input_file_id:
                delete_file(client, input_file_id, "input")
            if output_file_id:
                delete_file(client, output_file_id, "output")
        client.close()

    print()
    if exit_code == 0:
        print(green(bold("✓ Batch completed successfully.")))
        if results_path:
            print(f"  Output: {cyan(str(results_path))}")
    else:
        print(red(bold("✗ Batch did not complete successfully.")))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
