# Auto Router

The Auto Router lets callers set `model: "auto"` on any inference request. It classifies the request using an LLM, selects the most appropriate model from the live registry, and forwards the request transparently — no client changes required beyond setting the model field.

---

## Flow

```
Client request  (model="auto")
       │
       ▼
resolve_*_config()          ← finalises body.model (may inherit "auto" from key default)
       │
       ▼
_is_auto(body.model)?
  │ No  → normal path, zero overhead
  │ Yes ↓
       ▼
get_enabled_models(api_type)
  ├─ L1 cache hit  → Redis key routerv:models:autorouter:{type}   (filtered list, 5 min TTL)
  └─ L1 miss       → _get_models() (L2: routerv:models:list or DB) → filter → populate L1
       │
       ▼
call_classifier(candidates, user_content)
  ├─ asyncio.wait_for(adapter.chat_completion(...), timeout)
  ├─ success        → (model_id, "")
  ├─ TimeoutError   → (None, "classifier_timeout")
  └─ other error    → (None, "classifier_error")
       │
       ▼
parse_classifier_response(raw, valid_ids)
  ├─ valid ID in registry → return it
  └─ invalid / None       → None (→ fallback)
       │
       ▼
AutoRouteResult(resolved_model_id)
  └─ used_fallback=True when classifier failed or returned unknown ID
       │
       ▼
body = body.model_copy(update={"model": resolved_model_id})
       │
       ▼
normal inference path  (check_balance, resolve_routing, adapter, usage log …)
       │
       ▼
Response with metadata injected
  ├─ non-streaming  → x_auto_routed, x_resolved_model_id in response body
  └─ streaming      → X-Auto-Routed, X-Resolved-Model-Id headers
```

---

## Configuration

All settings are read from environment variables via Pydantic Settings.

| Variable | Default | Description |
|---|---|---|
| `AUTO_ROUTER_ENABLED` | `true` | Set to `false` to disable; `model="auto"` returns HTTP 400 |
| `AUTO_ROUTER_CLASSIFIER_MODEL_ID` | `auto-classifier-default` | Model ID used for the classifier call |
| `AUTO_ROUTER_FALLBACK_MODEL_ID` | *(empty)* | **Required** — model to use when classifier fails. Must be in the enabled registry |
| `AUTO_ROUTER_CLASSIFIER_TIMEOUT_MS` | `5000` | Max milliseconds to wait for the classifier response |
| `AUTO_ROUTER_CLASSIFIER_MAX_TOKENS` | `16` | Max tokens the classifier may produce (one model ID is enough) |
| `AUTO_ROUTER_CLASSIFIER_TEMPERATURE` | `0.0` | Temperature for the classifier (deterministic by default) |

---

## Supported Endpoints

| Endpoint | API Type | Streaming |
|---|---|---|
| `POST /v1/chat/completions` | `completions` | Yes — metadata in headers |
| `POST /v1/responses` | `responses` | Yes — metadata in headers |
| `POST /v1/embeddings` | `embeddings` | No |

---

## Request Examples

### Chat Completions

```bash
curl https://api.example.com/v1/chat/completions \
  -H "Authorization: Bearer rsk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Write a Python quicksort implementation"}]
  }'
```

### Responses API

```bash
curl https://api.example.com/v1/responses \
  -H "Authorization: Bearer rsk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "input": "Explain quantum entanglement simply"
  }'
```

### Embeddings

```bash
curl https://api.example.com/v1/embeddings \
  -H "Authorization: Bearer rsk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "input": "The quick brown fox jumps over the lazy dog"
  }'
```

---

## Response Metadata

### Non-streaming (body fields)

```json
{
  "id": "chatcmpl-...",
  "model": "openai/gpt-4o",
  "choices": [...],
  "x_auto_routed": true,
  "x_resolved_model_id": "openai/gpt-4o"
}
```

When the fallback model was used:

```json
{
  "x_auto_routed": true,
  "x_resolved_model_id": "openai/gpt-4o-mini",
  "x_auto_routed_fallback": true,
  "x_auto_routed_fallback_reason": "classifier_timeout"
}
```

### Streaming (response headers)

```
X-Auto-Routed: true
X-Resolved-Model-Id: openai/gpt-4o
```

When the fallback model was used:

```
X-Auto-Routed: true
X-Resolved-Model-Id: openai/gpt-4o-mini
X-Auto-Routed-Fallback: true
X-Auto-Routed-Fallback-Reason: classifier_timeout
```

---

## Fallback Behavior

The Auto Router never blocks a request due to its own failure. When the classifier cannot resolve a model, it falls back to `AUTO_ROUTER_FALLBACK_MODEL_ID`.

| Fallback Reason | Trigger |
|---|---|
| `empty_registry` | No enabled models found for the requested API type |
| `classifier_timeout` | Classifier LLM did not respond within `AUTO_ROUTER_CLASSIFIER_TIMEOUT_MS` |
| `classifier_error` | Adapter raised an exception, or the response had no choices |
| `invalid_response` | Classifier returned a model ID not present in the enabled registry |

**Configuration errors that return HTTP 500:**

- `AUTO_ROUTER_FALLBACK_MODEL_ID` is empty or not set
- `AUTO_ROUTER_FALLBACK_MODEL_ID` is set but the model is not in the enabled registry (when the registry is non-empty)

---

## Caching

The registry uses a two-level Redis cache to minimise DB round-trips.

| Level | Key | TTL | Content |
|---|---|---|---|
| L1 | `routerv:models:autorouter:{type}` | 300 s | Filtered `CandidateModel` list for the given API type |
| L2 | `routerv:models:list` | 300 s | All enabled models (shared with `GET /v1/models`) |

Both layers are invalidated when the admin API modifies models or model prices.

---

## Observability

### Prometheus Metrics

| Metric | Type | Description |
|---|---|---|
| `gateway_auto_router_requests_total` | Counter | Total requests processed by the Auto Router |
| `gateway_auto_router_fallback_total{reason}` | Counter | Fallback requests, labelled by reason |
| `gateway_auto_router_classifier_latency_ms` | Histogram | Classifier LLM call latency (ms) |

### Structured Logs

| Event | Level | Fields |
|---|---|---|
| `auto_router.triggered` | info | `request_id`, `api_type`, `candidate_model_count` |
| `auto_router.model_resolved` | info | `request_id`, `resolved_model_id`, `resolution_method` |
| `auto_router.fallback_used` | warning | `request_id`, `fallback_reason`, `fallback_model_id` |
| `auto_router.misconfigured` | error | `request_id`, `detail` |
| `classifier_call_complete` | debug | `request_id`, `elapsed_ms` |
| `classifier_timeout` | warning | `request_id`, `timeout_ms`, `elapsed_ms` |
| `classifier_error` | warning | `request_id`, `error`, `elapsed_ms` |
| `classifier_invalid_response` | warning | `raw_response`, `first_line` |

---

## Module Layout

```
app/auto_router/
  __init__.py       empty
  registry.py       get_enabled_models(api_type) → list[CandidateModel]
  classifier.py     call_classifier / parse_classifier_response / _build_user_message
  service.py        resolve_auto_model + router helpers (_is_auto, _inject_auto_route_meta, _auto_route_headers)

app/models/
  __init__.py       empty
  cache.py          MODELS_CACHE_KEY, MODELS_CACHE_TTL, invalidate_models_cache()

tests/auto_router/
  test_registry.py
  test_classifier.py
  test_service.py
```

---

## Classifier Billing

The classifier call is made with the system `OPENROUTER_API_KEY` and `owner=None`. It never appears in per-user usage logs or spend-cap accounting — the cost is billed to the operator, not the end user.
