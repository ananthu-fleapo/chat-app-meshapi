# Multi-Model Comparison API

`POST /v1/chat/compare` fans out a single conversation to multiple AI models in parallel, then (optionally) uses a comparison LLM to synthesize a structured evaluation of all responses.

---

## How It Works

1. **Fan-out**: All models in `models[]` are called concurrently. Wall-clock time is roughly that of the slowest model, not the sum.
2. **Error isolation**: If a model fails or times out, the others continue unaffected. Partial results are returned with `partial: true`.
3. **Synthesis** *(default)*: After all fan-out models respond, a comparison LLM analyzes the responses and produces a structured evaluation covering accuracy, completeness, clarity, and a recommendation.
4. **Skip synthesis** *(optional)*: Set `skip_comparison: true` to skip the synthesis step and get raw model outputs only — useful for parallel streaming UIs that do their own comparison.
5. **Usage tracking**: Each model call + the comparison call are logged as separate usage events.

---

## Endpoint

```
POST /v1/chat/compare
Authorization: Bearer rsk_<your-key>
Content-Type: application/json
```

---

## Request

```json
{
  "models": ["openai/gpt-4o", "anthropic/claude-3-5-sonnet"],
  "messages": [
    {"role": "user", "content": "Explain quantum entanglement simply."}
  ],
  "comparison_model": "openai/gpt-4o-mini",
  "comparison_instructions": "Focus on accuracy and accessibility for a general audience.",
  "temperature": 0.7,
  "max_tokens": 500,
  "stream": false,
  "skip_comparison": false
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `models` | `string[]` | Yes | Model IDs to compare. Min 1, max 10. Duplicates are deduplicated. |
| `messages` | `Message[]` | Yes | Conversation history (same format as `/v1/chat/completions`). |
| `comparison_model` | `string` | No | Model used for synthesis. Defaults to `COMPARE_DEFAULT_MODEL` env var (`openai/gpt-4o-mini`). Not required when `skip_comparison: true`. |
| `comparison_instructions` | `string` | No | Custom evaluation rubric injected into the comparison LLM's system prompt. |
| `model_overrides` | `ModelOverride[]` | No | Per-model parameter overrides (see below). |
| `temperature` | `float` | No | Applied to all fan-out models. Per-model overrides take precedence. |
| `max_tokens` | `int` | No | Applied to all fan-out models. Per-model overrides take precedence. |
| `stream` | `bool` | No | Default `false`. Set `true` for SSE streaming. |
| `skip_comparison` | `bool` | No | Default `false`. Set `true` to skip the synthesis LLM and return raw model outputs only. When combined with `stream: true`, each model streams token-by-token in real time. |

### Per-model overrides

```json
{
  "model_overrides": [
    {"model": "openai/gpt-4o", "temperature": 0.9},
    {
      "model": "anthropic/claude-3-5-sonnet",
      "max_tokens": 200,
      "system_prompt": "Be concise. Answer in one sentence."
    }
  ]
}
```

| Field | Description |
|---|---|
| `model` | Model ID this override applies to |
| `temperature` | Override temperature for this model only |
| `max_tokens` | Override max_tokens for this model only |
| `system_prompt` | Prepended as a system message for this model only |

---

## Response (non-streaming)

```json
{
  "comparison_id": "cmp_3f9a2b1c4d5e6f7a8b9c",
  "object": "compare.completion",
  "created": 1746230400,
  "models": ["openai/gpt-4o", "anthropic/claude-3-5-sonnet"],
  "results": [
    {
      "model": "openai/gpt-4o",
      "content": "Quantum entanglement is when two particles...",
      "response_body": { "...": "full upstream response" },
      "latency_ms": 1823,
      "error": null,
      "error_code": null,
      "usage": {
        "prompt_tokens": 12,
        "completion_tokens": 198,
        "total_tokens": 210
      },
      "request_id": "req_01J...::openai/gpt-4o"
    },
    {
      "model": "anthropic/claude-3-5-sonnet",
      "content": "When two particles become entangled...",
      "response_body": { "...": "full upstream response" },
      "latency_ms": 2041,
      "error": null,
      "error_code": null,
      "usage": {
        "prompt_tokens": 12,
        "completion_tokens": 162,
        "total_tokens": 174
      },
      "request_id": "req_01J...::anthropic/claude-3-5-sonnet"
    }
  ],
  "comparison": "Both responses are accurate. GPT-4o uses a more vivid analogy that aids comprehension. Claude is more concise. For a general audience, GPT-4o is recommended.",
  "comparison_model": "openai/gpt-4o-mini",
  "comparison_usage": {
    "prompt_tokens": 450,
    "completion_tokens": 92,
    "total_tokens": 542
  },
  "comparison_fallback_used": false,
  "total_latency_ms": 4210,
  "partial": false,
  "skip_comparison": false
}
```

### Response fields

| Field | Description |
|---|---|
| `comparison_id` | Stable ID for this comparison (prefix `cmp_`) |
| `models` | Deduplicated model list in the order submitted |
| `results` | One entry per model. Always present even on failure. |
| `results[].error` | `null` on success. Human-readable error string on failure. |
| `results[].error_code` | `null` \| `"gateway_timeout"` \| `"model_not_found"` \| `"upstream_error"` |
| `comparison` | LLM-synthesized verdict. `null` if synthesis failed, was skipped, or only 1 model responded. |
| `comparison_model` | Which model generated the comparison. `null` if synthesis was skipped or failed. |
| `comparison_usage` | Token usage for the comparison LLM call. `null` if synthesis was skipped. |
| `comparison_fallback_used` | `true` if the primary comparison model failed and a fallback was used. |
| `total_latency_ms` | Wall-clock time from fan-out start to synthesis complete. |
| `partial` | `true` when 1+ models failed but at least one succeeded. |
| `skip_comparison` | Echoes the request field. `true` means no synthesis was performed. |

---

## Streaming (SSE)

Set `"stream": true`. The response is a `text/event-stream` with typed events. Two modes:

### Mode 1: With comparison (`skip_comparison: false`, default)

Fan-out is non-streaming (full response collected per model), then the comparison LLM streams token-by-token.

| Event | When | Payload |
|---|---|---|
| `meta` | Immediately after auth | `{"comparison_id", "models", "comparison_model", "skip_comparison": false}` |
| `model_chunk` | As each fan-out model finishes (live, out of order) | `{"model", "delta", "latency_ms", "error", "error_code", "usage"}` |
| `model_done` | All fan-out results collected | `{"results": [...]}` (full results array) |
| `comparison_chunk` | During comparison LLM streaming | `{"delta": "<token>", "finish_reason": null \| "stop"}` |
| `done` | All complete | `{"comparison_id", "total_latency_ms", "partial", "comparison_model", "comparison_fallback_used"}` |

### Mode 2: Skip comparison (`skip_comparison: true`)

Each fan-out model streams tokens in real time concurrently, tagged by model name. No comparison LLM is called.

| Event | When | Payload |
|---|---|---|
| `meta` | Immediately after auth | `{"comparison_id", "models", "comparison_model": null, "skip_comparison": true}` |
| `model_chunk` | Each token from any model | `{"model": "...", "delta": "Hello", "finish_reason": null}` |
| `model_stream_done` | One model's stream ends | `{"model": "...", "finish_reason": "stop", "usage": {...}, "error": null \| "..."}` |
| `done` | All models finished | `{"comparison_id", "total_latency_ms", "partial", "skip_comparison": true}` |

`delta` contains the token text. `finish_reason` is `null` for mid-stream chunks and `"stop"` (or another stop reason) on the final content chunk. `usage` in `model_stream_done` contains the full token counts for that model.

### Example: with comparison

```
event: meta
data: {"comparison_id": "cmp_abc...", "models": ["gpt-4o", "claude-3-5-sonnet"], "comparison_model": "gpt-4o-mini", "skip_comparison": false}

event: model_chunk
data: {"model": "gpt-4o", "delta": "...", "latency_ms": 1800, "error": null, "usage": {...}}

event: model_chunk
data: {"model": "claude-3-5-sonnet", "delta": "...", "latency_ms": 2100, "error": null, "usage": {...}}

event: model_done
data: {"results": [...]}

event: comparison_chunk
data: {"delta": "Both", "finish_reason": null}

event: done
data: {"comparison_id": "cmp_abc...", "total_latency_ms": 4500, "partial": false, "comparison_model": "gpt-4o-mini", "comparison_fallback_used": false}
```

### Example: skip comparison (real-time per-model streaming)

```
event: meta
data: {"comparison_id": "cmp_xyz...", "models": ["gpt-4o", "claude-3-5-sonnet"], "comparison_model": null, "skip_comparison": true}

event: model_chunk
data: {"model": "gpt-4o", "delta": "Hello", "finish_reason": null}

event: model_chunk
data: {"model": "claude-3-5-sonnet", "delta": "Hi", "finish_reason": null}

event: model_stream_done
data: {"model": "gpt-4o", "finish_reason": "stop", "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}, "error": null}

event: model_stream_done
data: {"model": "claude-3-5-sonnet", "finish_reason": "stop", "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}, "error": null}

event: done
data: {"comparison_id": "cmp_xyz...", "total_latency_ms": 2100, "partial": false, "skip_comparison": true}
```

---

## Error responses

### All models failed (502)

```json
{
  "detail": {
    "error": {
      "code": "all_models_failed",
      "message": "All models returned errors.",
      "details": [
        {"model": "model-a", "error": "upstream 500", "error_code": "upstream_error"},
        {"model": "model-b", "error": "Model timed out after 120s.", "error_code": "gateway_timeout"}
      ]
    }
  }
}
```

### Validation error (422)

Standard RouterV validation envelope, e.g. when `models` has > 10 entries or `comparison_model` is not configured and `skip_comparison` is false.

### Rate limit (429)

Standard RouterV `Retry-After` header + error envelope.

---

## Behaviour notes

- **Rate limiting**: Counted as **1 request** against your key's RPM/RPD. The N+1 upstream calls are not counted individually.
- **Partial failures**: When some models fail and at least one succeeds, the comparison LLM runs on successful results only. `partial: true` is set in the response.
- **Single-model requests**: Valid. The comparison step is skipped and `comparison: null` is returned.
- **Deduplication**: Duplicate model IDs are silently removed (order preserved).
- **Max models**: 10 per request (configurable via `COMPARE_MAX_MODELS` env var).
- **Per-model timeout**: Each fan-out model has a 120s hard timeout (configurable via `COMPARE_MODEL_TIMEOUT_S`). A timeout on one model does not abort others.
- **Comparison fallback**: If the primary comparison model fails, the gateway tries fallback models in order (configured via `COMPARE_FALLBACK_MODELS`). `comparison_fallback_used: true` is set if a fallback was used.
- **Billing**: N+1 usage events are created — one for each fan-out model and one for the comparison call. Each appears in your usage dashboard with sub-request ID `<outer_id>::<model>` or `<outer_id>::comparison`. With `skip_comparison: true`, only N events fire (no comparison call).
- **Comparison LLM temperature**: Always `0.3` for deterministic, consistent evaluations. Not configurable per-request.

---

## Configuration

| Env var | Default | Description |
|---|---|---|
| `COMPARE_DEFAULT_MODEL` | `openai/gpt-4o-mini` | Default comparison model when `comparison_model` is omitted from the request. |
| `COMPARE_MAX_MODELS` | `10` | Hard ceiling on models per request. |
| `COMPARE_MODEL_TIMEOUT_S` | `120.0` | Per-model hard timeout in seconds for fan-out calls (both streaming and non-streaming). |
| `COMPARE_FALLBACK_MODELS` | `anthropic/claude-3-5-haiku,google/gemini-2.0-flash-001` | Comma-separated fallback models tried in order if the primary comparison model fails. |

---

## curl examples

### Non-streaming with comparison

```bash
curl -X POST https://api.meshapi.ai/v1/chat/compare \
  -H "Authorization: Bearer rsk_<your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "models": ["openai/gpt-4o", "anthropic/claude-3-5-sonnet"],
    "messages": [{"role": "user", "content": "What is the capital of France?"}],
    "comparison_model": "openai/gpt-4o-mini"
  }'
```

### Non-streaming, skip comparison

```bash
curl -X POST https://api.meshapi.ai/v1/chat/compare \
  -H "Authorization: Bearer rsk_<your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "models": ["openai/gpt-4o", "anthropic/claude-3-5-sonnet"],
    "messages": [{"role": "user", "content": "What is the capital of France?"}],
    "skip_comparison": true
  }'
```

### Streaming with comparison

```bash
curl -N -X POST https://api.meshapi.ai/v1/chat/compare \
  -H "Authorization: Bearer rsk_<your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "models": ["openai/gpt-4o", "anthropic/claude-3-5-sonnet"],
    "messages": [{"role": "user", "content": "What is the capital of France?"}],
    "comparison_model": "openai/gpt-4o-mini",
    "stream": true
  }'
```

### Real-time per-model streaming (skip comparison)

```bash
curl -N -X POST https://api.meshapi.ai/v1/chat/compare \
  -H "Authorization: Bearer rsk_<your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "models": ["openai/gpt-4o", "anthropic/claude-3-5-sonnet"],
    "messages": [{"role": "user", "content": "Count to 5."}],
    "stream": true,
    "skip_comparison": true
  }'
```

### With per-model overrides

```bash
curl -X POST https://api.meshapi.ai/v1/chat/compare \
  -H "Authorization: Bearer rsk_<your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "models": ["openai/gpt-4o", "anthropic/claude-3-5-sonnet", "google/gemini-2.0-flash-001"],
    "messages": [{"role": "user", "content": "Write a haiku about recursion."}],
    "comparison_model": "openai/gpt-4o-mini",
    "comparison_instructions": "Evaluate creativity, adherence to haiku form, and technical accuracy.",
    "model_overrides": [
      {"model": "anthropic/claude-3-5-sonnet", "temperature": 0.9},
      {"model": "google/gemini-2.0-flash-001", "max_tokens": 100}
    ]
  }'
```
