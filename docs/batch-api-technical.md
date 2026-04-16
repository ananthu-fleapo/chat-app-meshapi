# Batch API — Technical Reference

Last updated: 2026-04-16

---

## Overview

The Batch API proxies OpenAI-compatible async batch processing to any upstream provider that implements the batch adapter methods. Routing is model-based — the customer never specifies a provider. The provider is resolved from `model_prices` at file upload time, stored in `batch_files`, and carried through to `batch_jobs`.

---

## Endpoints

| Method | Path | Auth |
|---|---|---|
| `POST` | `/v1/files` | `rsk_` key |
| `GET` | `/v1/files/{file_id}` | `rsk_` key |
| `DELETE` | `/v1/files/{file_id}` | `rsk_` key |
| `GET` | `/v1/files/{file_id}/content` | `rsk_` key |
| `POST` | `/v1/batches` | `rsk_` key |
| `GET` | `/v1/batches` | `rsk_` key |
| `GET` | `/v1/batches/{batch_id}` | `rsk_` key |
| `POST` | `/v1/batches/{batch_id}/cancel` | `rsk_` key |

---

## Request Flow

### `POST /v1/files`

Request body:
```json
{
  "purpose": "batch",
  "requests": [
    {
      "custom_id": "req-1",
      "method": "POST",
      "url": "/v1/chat/completions",
      "body": {"model": "openai/gpt-4o-mini", "messages": [...], "max_tokens": 200}
    }
  ]
}
```

`method` defaults to `"POST"`, `url` defaults to `"/v1/chat/completions"` if omitted.

1. Rate-limit check (RPM/RPD via Redis).
2. Serialize `requests` array to JSONL bytes (`json.dumps` per item, newline-joined).
3. **Resolve models** — `_resolve_and_map_models(requests, db)`:
   - Iterates over all `BatchRequestItem` objects, collecting every distinct `body.model` value. Raises `400 invalid_batch_file` if none found.
   - For each unique raw model: `_resolve_canonical_model(raw, db)` tries exact `model_prices.model_id` match first, then `model_prices.provider_model_id` match. Raises `404 model_not_found` if neither found or model disabled.
   - `resolve_routing(canonical, db)` → `(provider, provider_model_id, ...)` for each canonical model.
   - Raises `400 mixed_providers` if any two models resolve to different providers — a batch file must be provider-scoped.
   - Returns `(first_canonical_model, shared_provider, {raw_model -> upstream_model_id})` where `upstream_model_id = provider_model_id or canonical_model_id`.
4. **Rewrite model IDs** — JSONL is built from the request list with each `body.model` replaced by its `upstream_model_id` so the provider receives its own native model string (e.g. `"gpt-4o-mini-2024-07-18"` instead of `"openai/gpt-4o-mini"`).
6. `_provider_adapter(provider)` — verifies adapter is registered (503) and implements batch (501).
7. `resolve_upstream_key(owner, provider, db)` — per-owner or system key from GCP Secret Manager.
8. Upload bytes to provider via `adapter.upload_file(...)`.
9. Write `BatchFile(file_id, owner, key_id, model, provider)` to DB.
10. Return provider file object.

**Key point:** the model and provider are resolved once at upload time and stored in `batch_files`. Subsequent endpoints look up `batch_files.file_id` — the customer never repeats the model.

---

### `POST /v1/batches`

Request body:
```json
{
  "input_file_id": "file-xxx",
  "endpoint": "/v1/chat/completions",
  "completion_window": "24h",
  "metadata": {}
}
```

1. Rate-limit check.
2. Concurrent batch limit — count `batch_jobs` where `owner = key.owner` and `status NOT IN (completed, failed, cancelled, expired)`. Raises `429 batch_limit_exceeded` if ≥ 10.
3. Look up `batch_files` by `file_id + owner`. Raises `404 file_not_found` if not found or belongs to a different owner.
4. Get `model` and `provider` from the `BatchFile` row.
5. Call `adapter.create_batch(input_file_id, endpoint, completion_window, metadata)`.
6. Create `UsageEvent(status="pending", model, provider, ...)` — billing placeholder. `request_id` = upstream batch ID.
7. Create `BatchJob(batch_id, owner, key_id, model, provider, input_file_id, usage_event_id)`.
8. Commit and return provider batch object.

---

### `GET /v1/batches/{batch_id}`

1. Look up `BatchJob` by `batch_id` to get `provider`.
2. Proxy `adapter.get_batch(batch_id)` to upstream.
3. If batch status is terminal (`completed | failed | cancelled | expired`) and `usage_synced=False`: call `_maybe_sync(...)`.

---

### `GET /v1/files/{file_id}/content`

1. Look up `BatchJob` by `output_file_id` to get `provider` and `job`.
2. If `job` exists and `usage_synced=False`: fetch batch status, call `_maybe_sync(...)`.
3. Proxy `adapter.get_file_content(file_id)` and return raw bytes.

---

### `GET /v1/batches`

Returns MeshAPI's own `BatchJob` rows (unified across all providers) in the OpenAI list format. Does **not** proxy to any upstream — gives a consistent cross-provider view.

Supports cursor-based pagination: `after` (batch_id) + `limit` (1–100, default 20).

Response shape:
```json
{
  "object": "list",
  "data": [...],
  "has_more": true,
  "first_id": "batch_xxx",
  "last_id": "batch_yyy"
}
```

---

## Model Resolution

`_resolve_canonical_model(raw_model, db)` resolves in two steps:

| Step | Lookup | Example input | Result |
|---|---|---|---|
| 1 | `model_prices.model_id` | `"openai/gpt-4o-mini"` | `"openai/gpt-4o-mini"` |
| 2 | `model_prices.provider_model_id` | `"gpt-4o-mini-2024-07-18"` | `"openai/gpt-4o-mini"` |

Both steps require `models.is_enabled=True`. Raises `UnsupportedModelError` (404 `model_not_found`) if neither matches.

This lets customers put either the canonical MeshAPI model ID or the raw upstream model ID in their JSONL — both are accepted.

---

## Billing

A `UsageEvent` row with `status="pending"` is created at `POST /v1/batches`. When the batch reaches a terminal state, the row is updated exactly once (guarded by `batch_jobs.usage_synced`).

### Terminal billing paths (first one wins)

| Path | Trigger |
|---|---|
| `GET /v1/batches/{batch_id}` | First poll that observes a terminal status |
| `GET /v1/files/{file_id}/content` | Direct output download (customer skips polling) |
| Background poller (`main.py`) | Fires every 60 s for all in-progress jobs in DB |

### `_sync_usage` flow

1. Download output JSONL via `adapter.get_file_content(output_file_id)`.
2. Parse via `adapter.parse_batch_results(content)` — provider-specific, returns per-request `{success, model, prompt_tokens, completion_tokens, cached_tokens}`.
3. Aggregate totals across successful requests only.
4. Apply account-level discount from `discounts` table.
5. Update `UsageEvent` → `status="success"`, token counts, `cost_usd`.
6. `deduct_balance(owner, total_cost)`.

For `failed | cancelled | expired`: update `UsageEvent` → `status="error"`, no balance deduction.

### Idempotency

`_maybe_sync` sets `batch_jobs.usage_synced=True` before spawning the background task. Any concurrent path that checks `usage_synced` before calling `_maybe_sync` will skip. This prevents double-billing when all three paths trigger close together.

---

## Database Tables

### `batch_files`

Tracks uploaded files. Written by `POST /v1/files`, read by `POST /v1/batches`.

| Column | Type | Notes |
|---|---|---|
| `file_id` | TEXT PK | Upstream provider file ID |
| `owner` | TEXT | Owner label from uploading API key |
| `key_id` | UUID | API key that performed the upload |
| `model` | TEXT | Canonical model_id resolved from JSONL |
| `provider` | TEXT | Upstream provider slug |
| `created_at` | TIMESTAMPTZ | Insert time |

Index: `ix_batch_files_owner`

### `batch_jobs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Internal row ID |
| `batch_id` | TEXT UNIQUE | Upstream provider batch ID |
| `owner` | TEXT | Owner label |
| `key_id` | UUID | API key that created the batch |
| `model` | TEXT | Canonical model_id |
| `provider` | TEXT | Upstream provider slug |
| `input_file_id` | TEXT | Provider file ID of uploaded JSONL |
| `output_file_id` | TEXT nullable | Set when batch completes |
| `status` | TEXT | Last observed upstream status |
| `usage_synced` | BOOL | True once billing has fired |
| `usage_event_id` | UUID nullable | FK to `usage_events` |
| `created_at` | TIMESTAMPTZ | |
| `completed_at` | TIMESTAMPTZ nullable | When terminal status first observed |

Indexes: `ix_batch_jobs_batch_id`, `ix_batch_jobs_owner`, `ix_batch_jobs_provider`, `ix_batch_jobs_output_file_id`

---

## Provider Adapter Interface

To add batch support for a new provider, implement these 9 methods in its `ProviderAdapter` subclass:

```python
async def upload_file(self, file_bytes, filename, purpose, *, api_key=None) -> dict
async def get_file(self, file_id, *, api_key=None) -> dict
async def delete_file(self, file_id, *, api_key=None) -> dict
async def get_file_content(self, file_id, *, api_key=None) -> bytes
async def create_batch(self, input_file_id, endpoint, completion_window, metadata=None, *, api_key=None) -> dict
async def get_batch(self, batch_id, *, api_key=None) -> dict
async def list_batches(self, after=None, limit=20, *, api_key=None) -> dict
async def cancel_batch(self, batch_id, *, api_key=None) -> dict
def parse_batch_results(self, content: bytes) -> list[dict]
```

`parse_batch_results` must return one dict per request with keys: `success` (bool), `model` (canonical model_id), `prompt_tokens`, `completion_tokens`, `cached_tokens` (all int).

Batch support is detected at runtime via duck-type check — no registration or capability flag needed.

Currently implemented: `OpenAIDirectAdapter`.

---

## Concurrent Batch Limit

10 active (non-terminal) batches per owner. `POST /v1/batches` returns `429 batch_limit_exceeded` when this ceiling is hit. Adjust `_MAX_ACTIVE_BATCHES` in `batch.py` to change the limit.

---

## Provider Routing for File Endpoints

`_provider_from_file_id(file_id, db)` lookup order:

1. `batch_files.file_id` — input files uploaded after migration 0037.
2. `batch_jobs.input_file_id` / `batch_jobs.output_file_id` — output files and backward compat.
3. Fallback: `"openai"` — files predating both tables.

---

## Migrations

| Migration | Change |
|---|---|
| `0032_batch_jobs` | Creates `batch_jobs` table |
| `0036_batch_jobs_provider` | Adds `model`, `provider` columns to `batch_jobs` |
| `0038_batch_files` | Creates `batch_files` table |
| `0039_supports_batching` | Adds `supports_batching` flag to `model_prices` |
