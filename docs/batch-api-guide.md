# Batch API — User Guide

The Batch API lets you send large volumes of AI requests asynchronously at reduced cost. Instead of calling the inference endpoint one request at a time, you upload a file of requests, submit them as a batch, and download the results when they're ready.

---

## Authentication

All batch endpoints use the same `rsk_` API key as the inference API:

```
Authorization: Bearer rsk_your_key_here
```

---

## Quick Start

### 1. Prepare your requests

Build a JSON array of requests. Each item needs a `custom_id` and a `body` with the model and messages. `method` and `url` are optional (defaults: `POST` / `/v1/chat/completions`).

```json
[
  {
    "custom_id": "req-1",
    "body": {
      "model": "openai/gpt-4o-mini",
      "messages": [{"role": "user", "content": "Summarize the French Revolution."}],
      "max_tokens": 200
    }
  },
  {
    "custom_id": "req-2",
    "body": {
      "model": "openai/gpt-4o-mini",
      "messages": [{"role": "user", "content": "What is the capital of Japan?"}],
      "max_tokens": 50
    }
  }
]
```

> All requests must use the same provider. Different models are fine as long as they route to the same provider (e.g. `openai/gpt-4o` + `openai/gpt-4o-mini` is allowed; mixing an OpenAI model with a Bedrock model is not).

---

### 2. Upload the requests

```bash
curl -X POST https://api.yourdomain.com/v1/files \
  -H "Authorization: Bearer rsk_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "purpose": "batch",
    "requests": [
      {"custom_id": "req-1", "body": {"model": "openai/gpt-4o-mini", "messages": [{"role": "user", "content": "Summarize the French Revolution."}], "max_tokens": 200}},
      {"custom_id": "req-2", "body": {"model": "openai/gpt-4o-mini", "messages": [{"role": "user", "content": "What is the capital of Japan?"}], "max_tokens": 50}}
    ]
  }'
```

Response:
```json
{
  "id": "file-abc123",
  "object": "file",
  "bytes": 512,
  "created_at": 1713200000,
  "filename": "requests.jsonl",
  "purpose": "batch"
}
```

Save the `id` — you need it in the next step.

---

### 3. Create the batch

```bash
curl -X POST https://api.yourdomain.com/v1/batches \
  -H "Authorization: Bearer rsk_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "input_file_id": "file-abc123",
    "endpoint": "/v1/chat/completions",
    "completion_window": "24h"
  }'
```

Response:
```json
{
  "id": "batch_xyz789",
  "object": "batch",
  "status": "validating",
  "input_file_id": "file-abc123",
  "endpoint": "/v1/chat/completions",
  "completion_window": "24h",
  "request_counts": {"total": 2, "completed": 0, "failed": 0},
  "created_at": 1713200010
}
```

---

### 4. Poll for completion

```bash
curl https://api.yourdomain.com/v1/batches/batch_xyz789 \
  -H "Authorization: Bearer rsk_your_key"
```

The `status` field progresses through:

| Status | Meaning |
|---|---|
| `validating` | File is being checked |
| `in_progress` | Requests are being processed |
| `finalizing` | Collecting results |
| `completed` | All done — results are ready |
| `failed` | Processing failed |
| `cancelled` | Cancelled by request |
| `expired` | Not completed within 24 hours |

Poll every 30–60 seconds. Billing fires automatically once a terminal status is observed — you don't need to call any separate endpoint.

---

### 5. Download results

When `status` is `completed`, the response includes `output_file_id`. Download the results:

```bash
curl https://api.yourdomain.com/v1/files/file-results456/content \
  -H "Authorization: Bearer rsk_your_key" \
  -o results.jsonl
```

---

### 6. Parse the results

Each line in the output JSONL corresponds to one input request, matched by `custom_id`:

```json
{
  "id": "batch_req_...",
  "custom_id": "req-1",
  "response": {
    "status_code": 200,
    "body": {
      "choices": [{"message": {"content": "The French Revolution was..."}}],
      "usage": {"prompt_tokens": 18, "completion_tokens": 95}
    }
  },
  "error": null
}
```

Lines with `response.status_code != 200` or `error != null` indicate failed requests. The output file is not ordered — always match by `custom_id`.

---

### 7. Clean up (optional)

Delete the input and output files when you no longer need them:

```bash
curl -X DELETE https://api.yourdomain.com/v1/files/file-abc123 \
  -H "Authorization: Bearer rsk_your_key"

curl -X DELETE https://api.yourdomain.com/v1/files/file-results456 \
  -H "Authorization: Bearer rsk_your_key"
```

---

## Other Operations

### List your batches

```bash
curl "https://api.yourdomain.com/v1/batches?limit=20" \
  -H "Authorization: Bearer rsk_your_key"
```

Returns your batches across all providers, newest first. Use `after=<batch_id>` to paginate.

### Cancel a batch

```bash
curl -X POST https://api.yourdomain.com/v1/batches/batch_xyz789/cancel \
  -H "Authorization: Bearer rsk_your_key"
```

Partial results may still be available in the output file after cancellation.

---

## Models

Use the same model IDs as the inference API (e.g. `openai/gpt-4o-mini`). The provider is resolved automatically — you don't specify it.

Bare upstream model IDs (e.g. `gpt-4o-mini-2024-07-18`) are also accepted and resolved to the canonical MeshAPI ID.

To see available models: `GET /v1/models`.

---

## Limits

| Limit | Value |
|---|---|
| Max concurrent batches per account | 10 |
| Completion window | 24 hours |
| Max requests per file | Provider-dependent (OpenAI: 50,000) |
| Max file size | Provider-dependent (OpenAI: 200 MB) |

If you have 10 batches in progress, `POST /v1/batches` returns `429 batch_limit_exceeded`. Wait for some to reach a terminal state before submitting more.

---

## Billing

- A billing record is created when you submit a batch (`POST /v1/batches`).
- The actual cost is calculated when the batch completes, based on token usage across all successful requests.
- Failed, cancelled, or expired batches are not charged.
- Balance is deducted once when the terminal status is first observed — either via polling, downloading results, or automatically by the background monitor.

---

## Error Reference

| HTTP | `error_code` | Cause |
|---|---|---|
| 400 | `invalid_batch_file` | JSONL has no parseable `body.model` field on any line |
| 400 | `mixed_providers` | Requests use models from different providers |
| 404 | `model_not_found` | Model is not in the registry or is disabled |
| 404 | `file_not_found` | `input_file_id` not found or belongs to another account |
| 429 | `batch_limit_exceeded` | 10 active batches already in progress |
| 429 | `rate_limit_exceeded` | RPM or RPD limit hit |
| 501 | `not_implemented` | Model's provider does not support the Batch API |
| 503 | `provider_unavailable` | Provider adapter not configured on this instance |

---

## Automated Script

`scripts/run_batch.py` runs the full lifecycle end-to-end:

```bash
python scripts/run_batch.py \
  --api-key  rsk_your_key \
  --base-url http://localhost:8000 \
  --model    openai/gpt-4o-mini \
  --no-cleanup
```

The `--model` flag sets the model in the built-in sample requests. Pass `--input requests.json` to use your own JSON array file instead. The script posts the requests, creates the batch, polls until completion, downloads results, and prints a summary. Omit `--no-cleanup` to delete input/output files from the provider afterwards.
