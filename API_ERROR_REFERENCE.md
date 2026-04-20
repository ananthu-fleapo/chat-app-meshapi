# API Error Reference Guide

**Purpose:** Document all potential error sources in user-facing endpoints — what is already handled correctly and what are the real gaps.

**Scope:** 5 user-facing routers
- `app/routers/inference.py` — Chat Completions API
- `app/routers/responses.py` — Responses API (reasoning models)
- `app/routers/models.py` — Model listing
- `app/routers/templates.py` — Prompt templates
- `app/routers/embeddings.py` — Embeddings API

**Legend:** ✓ = already handled correctly | ⚠ = real gap, needs fix

---

## Per-Router Error Tables (Swagger-aligned)

Detailed per-endpoint error tables with HTTP status, `error_code`, circumstance, and category
are maintained in the `docs/` directory:

| Router file | Error map |
|---|---|
| `app/routers/inference.py` | [`docs/error_map_inference.md`](docs/error_map_inference.md) |
| `app/routers/responses.py` | [`docs/error_map_responses.md`](docs/error_map_responses.md) |
| `app/routers/models.py` | [`docs/error_map_models.md`](docs/error_map_models.md) |
| `app/routers/templates.py` | [`docs/error_map_templates.md`](docs/error_map_templates.md) |
| `app/routers/embeddings.py` | [`docs/error_map_embeddings.md`](docs/error_map_embeddings.md) |

All five route files now carry `responses={...}` annotations so every documented status code
appears in the Swagger UI at `/docs`.

---

---

## Table of Contents
1. [Responses API](#responses-api---post-v1responses)
2. [Chat Completions API](#chat-completions-api---post-v1chatcompletions)
3. [Models Listing](#models-listing---get-v1models)
4. [Templates CRUD](#templates-crud---v1templates)

---

## Responses API — POST /v1/responses

**Route:** `POST /v1/responses`
**Auth:** Bearer `rsk_<ULID>`
**Purpose:** Proxy to Responses API for reasoning models
**Paths:** Streaming and non-streaming

### Error Sources

| # | Error Category | Location | Trigger | Actual Behavior | Status |
|---|---|---|---|---|---|
| **1** | **Rate Limiting - Redis** | `check_rate_limits()` | Redis unavailable, timeout | Fails **open** — exception caught, `logger.warning` emitted, request proceeds normally. Intentional design: a Redis blip must not take down the API. | ✓ No error returned |
| **2** | **Spend Cap Check - Database** | `check_spend_cap()` | PostgreSQL failure, query timeout | No exception handling. DB failure propagates as **500**. | ⚠ Needs 503 |
| **3** | **Config Resolution** | `resolve_responses_config()` | Invalid request schema | Pydantic validation (422) fires before this at FastAPI request binding. `resolve_responses_config` is a pure sync function; unlikely to raise outside of a programming error. | ✓ 422 handled by FastAPI |
| **4** | **Balance Check - Database** | `check_balance()` | PostgreSQL failure, query timeout | No exception handling on the DB query. DB failure propagates as **500**. | ⚠ Needs 503 |
| **5** | **Free Model Rate Limit - Redis** | `check_free_model_rate_limits()` | Redis unavailable | Same fail-open policy as #1 — exception caught, `logger.warning`, request proceeds. | ✓ No error returned |
| **6** | **Model Routing - Database** | `resolve_routing()` | Model not in `model_prices` | Never raises. Falls back to `("openrouter", None, None)` and forwards the original model ID to OpenRouter. Unknown models receive an upstream error from OpenRouter, not a 404 from RouterV. | ✓ No RouterV error (upstream handles it) |
| **7** | **Provider Capability Check - Database** | `db.get(ModelPrice, ...)` | DB unavailable | If `_price_row` is `None` (not found), the check is **skipped** and the request continues. If the DB query itself raises, no exception handling exists → **500**. | ⚠ DB failure needs 503 |
| **8** | **Upstream Key Resolution - GCP Secret Manager** | `resolve_upstream_key()` → `fetch_secret()` | GCP Secret Manager unavailable, secret missing | Caught and handled: falls back to system default key (`settings.openrouter_api_key`) with a `logger.warning`. | ✓ Graceful fallback |
| **8b** | **Upstream Key Resolution - Database** | `resolve_upstream_key()` → `_lookup_provider_key()` | PostgreSQL failure on `ProviderKey` lookup | No exception handling in `_lookup_provider_key`. DB failure propagates as **500**. | ⚠ Needs 503 |
| **9** | **Provider Adapter Not Found** | `get_adapter(provider)` | Provider slug not registered (missing credentials at startup) | Raises `ProviderNotAvailableError` → **503** with `{"error": {"code": "provider_not_available", "message": "Provider '...' is not available."}}`. | ✓ Already 503 |
| **10** | **Responses API Capability Guard** | `getattr(type(adapter), _needed)` check | Adapter does not implement `responses_create` or `stream_responses_create` | Raises `HTTPException(status_code=501)` — `"{model} does not have support for Responses API."` | ✓ Already 501 |
| **10b** | **Model Capability Check (DB-driven)** | `_price_row.supports_responses_api` check | Model explicitly marked as not supporting Responses API | Raises `ModelCapabilityError` → **400** with `{"error": {"code": "model_capability_not_supported", "message": "Model '...' does not support the responses API."}}` | ✓ Already 400 |
| **11** | **Streaming - Upstream API Failure** | `adapter.stream_responses_create()` | Provider API error, timeout, 5xx | Caught in `except Exception`. SSE error frame yielded: `data: {"error": {"code": "...", "message": "..."}}`. Status code cannot be changed (200 + `text/event-stream` headers already sent). | ✓ Handled via SSE error frame |
| **12** | **Streaming - SSE Frame Parsing** | `json.loads(payload)` inside generator | Malformed JSON in SSE chunk | `except (json.JSONDecodeError, KeyError): pass` — silently skipped. Stream continues uninterrupted. | ✓ Silent skip, stream unaffected |
| **13** | **Usage Data Normalization** | `_normalize_usage()` in finally | Malformed usage dict from provider | Input is always guarded as `(response_body or {}).get("usage") or {}` — always a dict. Keys are checked with `in` before `.pop()`. | ✓ Already safe |
| **14** | **Non-Streaming - Upstream API Failure** | `adapter.responses_create()` | Provider API error, timeout, auth failure | `except Exception` sets `status="error"` then **re-raises**. `RouterVError` subclasses → structured JSON response via exception handler. Raw exceptions from `httpx` (timeout, network) → unhandled **500**. | ⚠ Non-RouterVError upstreams need wrapping |
| **15** | **Usage Logging (Finally Block)** | `fire_usage_log()` | DB unavailable during logging | `fire_usage_log` calls `asyncio.create_task(log_usage_event(...))` — **never raises** in the finally block. Inside `log_usage_event`, Postgres failures are caught and logged; MongoDB is always attempted as fallback. | ✓ Fire-and-forget, fully exception-safe |

### Gaps Summary — Responses API

| Gap | Location | Suggested Fix |
|---|---|---|
| `check_spend_cap` DB failure → 500 | `spend_cap.py` | Wrap DB query in `try/except`; raise `HTTPException(503)` |
| `check_balance` DB failure → 500 | `balance.py` | Wrap DB query in `try/except`; raise `HTTPException(503)` |
| `db.get(ModelPrice)` DB failure → 500 | `responses.py` | Wrap in `try/except`; raise `HTTPException(503)` |
| `_lookup_provider_key` DB failure → 500 | `key_resolver.py` | Wrap in `try/except`; raise `HTTPException(503)` |
| Non-RouterVError upstream exceptions → 500 | `responses.py` non-streaming path | Catch `httpx.TimeoutException` → 504; `httpx.HTTPStatusError` → 502 |

---

## Chat Completions API — POST /v1/chat/completions

**Route:** `POST /v1/chat/completions`
**Auth:** Bearer `rsk_<ULID>`
**Purpose:** OpenAI-compatible chat completions endpoint
**Paths:** Streaming and non-streaming, with optional template support

### Error Sources

| # | Error Category | Location | Trigger | Actual Behavior | Status |
|---|---|---|---|---|---|
| **1** | **Rate Limiting - Redis** | `check_rate_limits()` | Redis unavailable | Fails open — same policy as Responses API #1. | ✓ No error returned |
| **2** | **Spend Cap Check - Database** | `check_spend_cap()` | PostgreSQL failure | No exception handling → **500**. | ⚠ Needs 503 |
| **3** | **Template Resolution - Database** | `resolve_template()` | Template not found | Raises `NotFoundError` → **404**. DB query failure (connection down): no exception handling → **500**. | ✓ Not Found | ⚠ DB failure needs 503 |
| **4** | **Template Rendering** | `render_template()` | Missing `{{variable}}` in supplied dict | Raises `UnprocessableEntityError` → **422** with `{"error": {"code": "unprocessable_entity", "message": "Template '...' requires variable '{{...}}' but it was not provided."}}` | ✓ Already 422 |
| **5** | **Config Resolution** | `resolve_config()` | Invalid request schema | Pydantic validation (422) fires before this. `resolve_config` is a pure sync function. | ✓ 422 handled by FastAPI |
| **6** | **Balance Check - Database** | `check_balance()` | PostgreSQL failure | No exception handling → **500**. | ⚠ Needs 503 |
| **7** | **Free Model Rate Limit - Redis** | `check_free_model_rate_limits()` | Redis unavailable | Fails open — same policy as #1. | ✓ No error returned |
| **8** | **Model Routing - Database** | `resolve_routing()` | Model not in `model_prices` | Falls back to `("openrouter", None, None)` — no error raised. Unknown models forwarded to OpenRouter. | ✓ No RouterV error |
| **9** | **Capability Check - Database** | `db.get(ModelPrice, ...)` | DB unavailable | If `_price_row` is `None`, check is skipped. DB query failure → **500**. | ⚠ DB failure needs 503 |
| **10** | **Upstream Key Resolution - GCP Secret Manager** | `resolve_upstream_key()` | GCP Secret Manager failure | Falls back to system default key with `logger.warning`. | ✓ Graceful fallback |
| **10b** | **Upstream Key Resolution - Database** | `_lookup_provider_key()` | PostgreSQL failure | No exception handling → **500**. | ⚠ Needs 503 |
| **11** | **Provider Adapter Not Found** | `get_adapter(provider)` | Provider not registered | Raises `ProviderNotAvailableError` → **503**. | ✓ Already 503 |
| **11b** | **Model Capability Check (DB-driven)** | `_price_row.supports_completions_api` | Model doesn't support chat/completions | Raises `ModelCapabilityError` → **400**. | ✓ Already 400 |
| **12** | **Streaming - Upstream API Failure** | `adapter.stream_chat_completion()` | Provider error, timeout, 5xx | Caught in `except Exception`. SSE error frame yielded. Status code cannot be changed after stream starts. | ✓ Handled via SSE error frame |
| **13** | **Streaming - SSE Frame Parsing** | `json.loads(payload)` inside generator | Malformed JSON in SSE chunk | `except (json.JSONDecodeError, KeyError): pass` — silent skip, stream continues. | ✓ Silent skip |
| **14** | **Streaming - Client Disconnect** | `request.is_disconnected()` check | Client disconnects mid-stream | Generator returns early with `log.info("stream_client_disconnected")`. Clean exit. | ✓ Already handled |
| **15** | **Non-Streaming - Upstream API Failure** | `adapter.chat_completion()` | Provider error, timeout, 5xx | `except Exception` sets status then **re-raises**. `RouterVError` subclasses → structured response. Raw `httpx` exceptions → **500**. | ⚠ Non-RouterVError upstreams need wrapping |
| **16** | **Usage Logging (Finally Block)** | `fire_usage_log()` | DB unavailable during logging | `asyncio.create_task` — never raises. `log_usage_event` exceptions caught internally with MongoDB fallback. | ✓ Fire-and-forget, fully exception-safe |
| **17** | **Response Body Access** | `response_body.get(...)` after non-streaming call | `response_body` is `None` when exception raised | `(response_body or {}).get("usage") or {}` guard ensures safe access. `response_body.get("model", ...)` on line 255 is only reached when no exception was raised. | ✓ Already safe |

### Gaps Summary — Chat Completions API

| Gap | Location | Suggested Fix |
|---|---|---|
| `check_spend_cap` DB failure → 500 | `spend_cap.py` | Wrap DB query; raise `HTTPException(503)` |
| `check_balance` DB failure → 500 | `balance.py` | Wrap DB query; raise `HTTPException(503)` |
| `resolve_template` DB query failure → 500 | `templates/resolver.py` | Wrap `db.execute()` calls; raise `HTTPException(503)` |
| `db.get(ModelPrice)` DB failure → 500 | `inference.py` | Wrap in `try/except`; raise `HTTPException(503)` |
| `_lookup_provider_key` DB failure → 500 | `key_resolver.py` | Wrap in `try/except`; raise `HTTPException(503)` |
| Non-RouterVError upstream exceptions → 500 | `inference.py` non-streaming path | Catch `httpx.TimeoutException` → 504; `httpx.HTTPStatusError` → 502 |

---

## Models Listing — GET /v1/models

**Routes:**
- `GET /v1/models` — List all enabled models with optional `?free=true/false` filter
- `GET /v1/models/free` — List free models only
- `GET /v1/models/paid` — List paid models only

**Auth:** Supabase JWT or Bearer `rsk_<ULID>`
**Cache:** Redis 5-minute TTL (invalidated on admin writes)

### Error Sources

| # | Error Category | Location | Trigger | Actual Behavior | Status |
|---|---|---|---|---|---|
| **1** | **Redis Cache Read Failure** | `redis.get()` in `_get_models()` | Redis unavailable, timeout | Caught by `except Exception` → `logger.warning("models_cache_read_failed")` → falls through to DB query. | ✓ Graceful fallback to DB |
| **2** | **Database Query Failure** | `session.execute(select(...))` in `_get_models()` | PostgreSQL unavailable, timeout | Caught by `except Exception` → `logger.warning("models_db_fetch_failed")` → **returns `[]`** (200 with empty list, not 500). | ✓ Returns empty list, not 500 |
| **3** | **Redis Cache Write Failure** | `redis.setex()` in `_get_models()` | Redis unavailable after DB query succeeded | Caught by `except Exception` → `logger.warning("models_cache_write_failed")` → DB result still returned to caller. | ✓ Non-fatal, data returned |
| **4** | **Discount Query Failure** | `db.execute(select(Discount...))` in `_apply_discounts()` | PostgreSQL failure, timeout | No exception handling. DB failure propagates as **500**. | ⚠ Should return models without discounts |
| **5** | **Decimal Arithmetic Error** | `Decimal(val) * multiplier` in `_discounted()` | Invalid Decimal format in price field | Caught by `except InvalidOperation: return val` — returns original undiscounted value. | ✓ Already safe |
| **6** | **JSON Serialization (Cache Roundtrip)** | `json.loads(cached)` / `json.dumps(...)` | Malformed cached JSON, non-serializable model data | Cache read: covered by `except Exception` handler at item #1. Cache write: covered by `except Exception` handler at item #3. | ✓ Both covered |

### Gaps Summary — Models Listing

| Gap | Location | Suggested Fix |
|---|---|---|
| `_apply_discounts` DB failure → 500 | `models.py` | Wrap `db.execute()` in `try/except`; log warning and return `models` unchanged (without discounts) |

```python
# In models.py _apply_discounts():
try:
    result_rows = await db.execute(select(Discount...).where(...))
    rows = result_rows.all()
except Exception as exc:
    logger.warning("discount_query_failed", owner=owner, error=str(exc))
    return models  # return without discount enrichment
```

---

## Templates CRUD — /v1/templates

**Routes:**
- `POST /v1/templates` — Create template
- `GET /v1/templates` — List user's templates
- `GET /v1/templates/{template_id}` — Get single template
- `PATCH /v1/templates/{template_id}` — Update template
- `DELETE /v1/templates/{template_id}` — Delete template

**Auth:** Supabase JWT

### POST /v1/templates — Create

| # | Error Category | Trigger | Actual Behavior | Status |
|---|---|---|---|---|
| **1** | **Duplicate Template Name** | Same name exists for owner | `IntegrityError` caught → **409** `"A template named '...' already exists for owner '...'"` | ✓ Correct |
| **2** | **Invalid Request Schema** | Pydantic validation fails | FastAPI → **422** | ✓ Correct |
| **3** | **DB Failure (flush/refresh)** | PostgreSQL unavailable, connection pool exhausted | Only `IntegrityError` is caught. Other DB exceptions → **500**. | ⚠ Needs 503 |

### GET /v1/templates — List

| # | Error Category | Trigger | Actual Behavior | Status |
|---|---|---|---|---|
| **1** | **DB Query Failure** | PostgreSQL unavailable, timeout | No exception handling → **500**. | ⚠ Needs 503 |

### GET /v1/templates/{template_id} — Get Single

| # | Error Category | Trigger | Actual Behavior | Status |
|---|---|---|---|---|
| **1** | **Invalid UUID Format** | `template_id` is not a valid UUID | `ValueError` caught in `_get_own_or_404` → `NotFoundError` → **404** | ✓ Correct |
| **2** | **Template Not Found / Not Owned** | Template doesn't exist or belongs to another owner | `scalar_one_or_none()` returns `None` → `NotFoundError` → **404** | ✓ Correct |
| **3** | **DB Query Failure** | PostgreSQL unavailable, timeout | No exception handling in `_get_own_or_404` → **500**. | ⚠ Needs 503 |

### PATCH /v1/templates/{template_id} — Update

| # | Error Category | Trigger | Actual Behavior | Status |
|---|---|---|---|---|
| **1** | **Template Not Found** | Template doesn't exist or belongs to another owner | `_get_own_or_404` → `NotFoundError` → **404** | ✓ Correct |
| **2** | **Duplicate Name After Update** | Updating name to one that already exists | `IntegrityError` caught → **409** | ✓ Correct |
| **3** | **Invalid Request Schema** | Pydantic validation fails | FastAPI → **422** | ✓ Correct |
| **4** | **DB Failure (flush/refresh)** | PostgreSQL unavailable | Only `IntegrityError` caught. Other DB exceptions → **500**. | ⚠ Needs 503 |

### DELETE /v1/templates/{template_id} — Delete

| # | Error Category | Trigger | Actual Behavior | Status |
|---|---|---|---|---|
| **1** | **Template Not Found** | Template doesn't exist or belongs to another owner | `_get_own_or_404` → `NotFoundError` → **404** | ✓ Correct |
| **2** | **DB Delete / Commit Failure** | PostgreSQL failure during delete or session commit | No exception handling → **500**. | ⚠ Needs 503 |

### Gaps Summary — Templates CRUD

| Gap | Endpoint | Suggested Fix |
|---|---|---|
| Non-`IntegrityError` DB failures in create → 500 | `POST /v1/templates` | Add `except Exception` after `except IntegrityError`; rollback and raise 503 |
| DB failure in list → 500 | `GET /v1/templates` | Wrap `db.execute()` in `try/except`; raise 503 |
| DB failure in get/update/delete → 500 | `GET/PATCH/DELETE` | Wrap `_get_own_or_404` and mutation steps in `try/except`; raise 503 |
| Non-`IntegrityError` DB failures in update → 500 | `PATCH /v1/templates/{id}` | Add `except Exception` after `except IntegrityError`; rollback and raise 503 |

```python
# Pattern for all CRUD DB failures:
try:
    await db.flush()
    await db.refresh(template)
except IntegrityError:
    await db.rollback()
    raise HTTPException(status_code=409, detail=f"A template named '{body.name}' already exists.")
except Exception as exc:
    await db.rollback()
    logger.error("template_db_error", error=str(exc))
    raise HTTPException(status_code=503, detail="Database temporarily unavailable. Retry in a moment.")
```

---

## Summary: HTTP Status Codes

### What RouterV Actually Returns Today

| Status | Where | Correct? |
|--------|---|---|
| **400** | `ModelCapabilityError` (model doesn't support API) | ✓ Correct |
| **401** | `UnauthorizedError` (invalid/missing API key) | ✓ Correct |
| **402** | `PaymentRequiredError` (spend cap, zero balance) | ✓ Correct |
| **404** | `NotFoundError`, `UnsupportedModelError`, `_get_own_or_404` | ✓ Correct |
| **409** | `IntegrityError` on duplicate template name | ✓ Correct |
| **422** | Pydantic validation, `UnprocessableEntityError` (missing template var) | ✓ Correct |
| **429** | `RateLimitError` with `Retry-After` header | ✓ Correct |
| **500** | Unhandled DB failures, raw upstream `httpx` exceptions | ⚠ Should be 503 or 502/504 |
| **501** | Adapter doesn't implement Responses API method | ✓ Correct |
| **503** | `ProviderNotAvailableError` (unconfigured provider credentials) | ✓ Correct |

### Real Gaps (things that return 500 but shouldn't)

| Scenario | Should Be | Files to Fix |
|---|---|---|
| PostgreSQL down during `check_spend_cap` | 503 | `app/usage/spend_cap.py` |
| PostgreSQL down during `check_balance` | 503 | `app/usage/balance.py` |
| PostgreSQL down during `_lookup_provider_key` | 503 | `app/providers/key_resolver.py` |
| PostgreSQL down during capability `db.get(ModelPrice)` | 503 | `app/routers/responses.py`, `app/routers/inference.py` |
| PostgreSQL down during `_apply_discounts` | 200 (skip discounts) | `app/routers/models.py` |
| PostgreSQL down during any Templates CRUD operation | 503 | `app/routers/templates.py` |
| `httpx.TimeoutException` from upstream provider | 504 | `app/routers/responses.py`, `app/routers/inference.py` |
| `httpx.HTTPStatusError` from upstream provider | 502 | `app/routers/responses.py`, `app/routers/inference.py` |

---

## Implementation Priority

### High Priority
1. **`spend_cap.py` and `balance.py`** — DB failures on every request path → 503
2. **`key_resolver.py`** — DB failure on every request path → 503
3. **`models.py` `_apply_discounts`** — DB failure kills model listing → return without discounts
4. **`templates.py`** — all CRUD DB failures → 503

### Medium Priority
1. **Upstream `httpx` exceptions** — wrap `TimeoutException` → 504, `HTTPStatusError` → 502 in both routers
2. **`responses.py` / `inference.py` capability `db.get()`** — DB failure → 503

### Already Correct (no changes needed)
- Redis rate limiting (fail-open is intentional)
- Model routing fallback (openrouter fallback is intentional)
- GCP Secret Manager fallback (system key fallback is intentional)
- All streaming error handling (SSE error frames)
- Usage logging (fire-and-forget background task)
- Template not-found (404 correct)
- Template variable errors (422 correct)
- Duplicate template names (409 correct)
- Models Redis cache failures (graceful fallback)
- Models DB failure (empty list, not 500)
