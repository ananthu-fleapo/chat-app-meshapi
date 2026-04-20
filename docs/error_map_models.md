# Error Map — `GET /v1/models`, `/v1/models/free`, `/v1/models/paid`

> Source: `app/routers/models.py`

All errors use the RouterV envelope:
```json
{"error": {"code": "<error_code>", "message": "..."}, "request_id": "req_..."}
```

---

## Error Table

| Endpoint | HTTP | `error_code` | Circumstance | Category |
|---|---|---|---|---|
| GET /v1/models | 401 | `unauthorized` | Neither a valid Supabase JWT nor a valid `rsk_` API key provided in the `Authorization` header | Platform |
| GET /v1/models | 500 | `internal_error` | Unhandled `SQLAlchemyError` inside `_apply_discounts()` — discount DB query fails (e.g. connection refused, schema mismatch) | Platform |
| GET /v1/models/free | 401 | `unauthorized` | Same as above | Platform |
| GET /v1/models/free | 500 | `internal_error` | Same as above — `_apply_discounts()` DB failure | Platform |
| GET /v1/models/paid | 401 | `unauthorized` | Same as above | Platform |
| GET /v1/models/paid | 500 | `internal_error` | Same as above — `_apply_discounts()` DB failure | Platform |

---

## Silently Degraded Cases (HTTP 200, Empty List)

These scenarios return HTTP 200 with an empty `[]` body — no error is surfaced to the caller:

| Situation | Where caught | Logged as |
|---|---|---|
| PostgreSQL connection failure during model list fetch | `_get_models()` broad `except` | `WARNING models_db_fetch_failed` |
| Redis connection failure during cache read | `_get_models()` broad `except` | `WARNING models_cache_read_failed` |
| Redis connection failure during cache write | `_get_models()` broad `except` | `WARNING models_cache_write_failed` |

---

## Notes

- The models list endpoint is **DB-only** — no upstream provider calls are made. The only upstream-dependent error path is the discount lookup in `_apply_discounts()`.
- Cache TTL is 5 minutes. Admin writes to `models` or `model_prices` immediately invalidate `routerv:models:list` in Redis.
- Discounts are **never cached** — they are fetched per-request per-user from the `discounts` table.
