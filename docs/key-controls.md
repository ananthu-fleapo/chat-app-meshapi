# API Key Controls — Model Access, Per-Model Caps, and TPM

## Overview

Beyond the base RPM/RPD rate limits and flat spend cap, API keys support three additional controls:

| Control | What it does | Enforced at |
|---|---|---|
| **Allowed Models** | Whitelist of model IDs the key may call | Pre-request (sync) |
| **Model Limits** | Per-model lifetime caps (cost, tokens, requests) | Pre-request (DB query) |
| **TPM** | Tokens-per-minute sliding rate limit | Pre-request (Redis) |

All three are checked inside `POST /v1/chat/completions` after rate-limit and spend-cap checks, before the upstream call.

---

## Request Flow (with new controls)

```
POST /v1/chat/completions
  → get_authenticated_key()
  → check_rate_limits()          RPM / RPD — Redis fixed-window
  → check_tpm_limit()            TPM — Redis current-minute bucket
  → check_spend_cap()            flat USD cap — DB aggregate
  → resolve_template()
  → resolve_config()             merge model from request / key default / template
  → check_balance()
  → check_allowed_models()       sync — no DB hit
  → check_model_limits()         async DB aggregate for (key_id, model)
  → provider adapter
  → fire_usage_log()
  → increment_tpm_counter()      async fire-and-forget after response
```

---

## 1. Allowed Models

### What it is

An optional whitelist of model IDs. When set, any request for a model not in the list is rejected with **403 Forbidden** before reaching the upstream.

### DB column

```
api_keys.allowed_models  TEXT[] NULL
```

`NULL` means unrestricted. An empty array clears the restriction (stored as `NULL`).

### Error response

```json
HTTP 403
{
  "error": {
    "message": "Model 'openai/gpt-4o' is not permitted for this API key.",
    "type": "forbidden",
    "code": 403
  }
}
```

### Setting via API

**User-facing (dashboard):**
```json
POST /v1/keys
{ "allowed_models": ["openai/gpt-4o", "anthropic/claude-3-5-sonnet"] }
```

**Admin:**
```json
POST /admin/keys
{ "allowed_models": ["openai/gpt-4o"] }

PATCH /admin/keys/{key_id}
{ "allowed_models": ["openai/gpt-4o", "google/gemini-2.0-flash-001"] }
```

Pass `"allowed_models": null` or `"allowed_models": []` in a PATCH to clear the restriction.

---

## 2. Model Limits

### What it is

Per-model lifetime caps stored as a JSONB object. Each key in the map is a model ID; the value specifies which caps to enforce. Any combination of the three cap types can be set — unset fields are ignored.

### DB column

```
api_keys.model_limits  JSONB NULL
```

### Schema

```json
{
  "openai/gpt-4o": {
    "max_cost_usd": 10.0,
    "max_tokens": 500000,
    "max_requests": 200
  },
  "anthropic/claude-3-5-sonnet": {
    "max_cost_usd": 5.0
  }
}
```

| Field | Type | Cap type |
|---|---|---|
| `max_cost_usd` | `float` | Lifetime cost for `(key, model)` in USD |
| `max_tokens` | `int` | Lifetime `total_tokens` for `(key, model)` |
| `max_requests` | `int` | Lifetime request count for `(key, model)` |

### Enforcement

One aggregate DB query per request (only when model limits are configured for the key):

```sql
SELECT
  COALESCE(SUM(cost_usd), 0)      AS total_cost,
  COALESCE(SUM(total_tokens), 0)  AS total_tokens,
  COUNT(id)                        AS total_requests
FROM usage_events
WHERE key_id = ? AND model = ?
```

If any cap is met or exceeded, the request is rejected **before** hitting the upstream.

### Soft-cap behaviour

Like `spend_cap`, model limits are checked pre-request. A single request can overshoot the cap by at most one request's worth of tokens/cost. This is an acceptable trade-off for LLM workloads where checking mid-stream is impractical.

### Error response

```json
HTTP 402
{
  "error": {
    "message": "Cost cap of $10.0 for model 'openai/gpt-4o' reached. Current spend: $10.002341.",
    "type": "payment_required",
    "code": 402
  }
}
```

Token and request cap messages follow the same pattern.

### Setting via API

**User-facing (dashboard):**
```json
POST /v1/keys
{
  "model_limits": {
    "openai/gpt-4o": { "max_cost_usd": 10.0, "max_requests": 200 }
  }
}
```

**Admin:**
```json
POST /admin/keys
{
  "model_limits": {
    "openai/gpt-4o": { "max_cost_usd": 10.0 },
    "anthropic/claude-3-5-sonnet": { "max_tokens": 1000000 }
  }
}

PATCH /admin/keys/{key_id}
{
  "model_limits": {
    "openai/gpt-4o": { "max_cost_usd": 20.0 }
  }
}
```

The entire `model_limits` object is replaced on PATCH — it is not merged with the existing value. Pass `null` to clear all model limits.

---

## 3. TPM (Tokens Per Minute)

### What it is

A sliding per-minute token budget enforced via Redis. The counter tracks tokens consumed in the current 60-second bucket. When the bucket total reaches `tpm_limit`, further requests are rejected with **429** until the bucket resets.

### DB column

```
api_keys.tpm_limit  INTEGER NULL
```

`NULL` means no TPM limit.

### Redis key pattern

```
routerv:rl:{key_id}:tpm:{epoch_minute}
```

Where `epoch_minute = int(time.time()) // 60`. TTL is **90 seconds** (same 1.5× overhang as RPM/RPD buckets).

### Check / increment flow

1. **Pre-request** — `check_tpm_limit()` reads the current bucket. If `count >= tpm_limit`, raises `RateLimitError(limit_type="tpm")`.
2. **Post-response** — `increment_tpm_counter()` is called as an `asyncio.create_task()` fire-and-forget after the response is sent, using the actual token count from the usage log. Works for both streaming and non-streaming.

Both functions fail open on Redis unavailability (same behaviour as RPM/RPD).

### Error response

```json
HTTP 429
{
  "error": {
    "message": "TPM limit of 100,000 tokens/min exceeded.",
    "type": "rate_limit_error",
    "code": 429,
    "limit_type": "tpm"
  }
}
```

### Setting via API

**User-facing (dashboard):**
```json
POST /v1/keys
{ "tpm": 100000 }
```

**Admin:**
```json
POST /admin/keys
{ "tpm_limit": 100000 }

PATCH /admin/keys/{key_id}
{ "tpm_limit": 50000 }
```

Note: the user-facing field name is `tpm`; the admin field name is `tpm_limit`.

---

## Combining Controls

All three controls can be used together on a single key. A request must pass every check in sequence. Example: a key might be restricted to two models, have a per-model token cap for the expensive one, and also have a TPM limit to prevent burst traffic.

```json
POST /admin/keys
{
  "owner": "user_abc",
  "allowed_models": ["openai/gpt-4o", "openai/gpt-4o-mini"],
  "model_limits": {
    "openai/gpt-4o": { "max_cost_usd": 10.0, "max_requests": 100 }
  },
  "tpm_limit": 200000,
  "rpm_limit": 60,
  "spend_cap_usd": 50.0
}
```

---

## Key Schema Reference

Fields returned in `KeySummary` (both user-facing and admin endpoints):

| Field | Type | Notes |
|---|---|---|
| `allowed_models` | `string[] \| null` | `null` = unrestricted |
| `model_limits` | `object \| null` | JSONB — see schema above |
| `tpm_limit` | `integer \| null` | `null` = no TPM limit |
| `rpm_limit` | `integer \| null` | Requests per minute; `null` = use plan default |
| `rpd_limit` | `integer \| null` | Requests per day; `null` = use plan default |
| `spend_cap_usd` | `string \| null` | Flat lifetime cap in USD |

---

## Implementation Files

| File | Role |
|---|---|
| `app/usage/model_limits.py` | `check_allowed_models()` and `check_model_limits()` |
| `app/cache/rate_limiter.py` | `check_tpm_limit()` and `increment_tpm_counter()` |
| `app/routers/inference.py` | Wires all checks into the request flow |
| `app/routers/keys.py` | User-facing CRUD — `CreateKeyRequest`, `KeySummary` |
| `app/routers/admin.py` | Admin CRUD — `CreateKeyRequest`, `UpdateKeyRequest`, `KeySummary` |
| `app/db/models.py` | `ApiKey` ORM — `allowed_models`, `model_limits`, `tpm_limit` columns |
| `backend/alembic/versions/0044_model_limits_tpm.py` | Migration adding the three columns |
