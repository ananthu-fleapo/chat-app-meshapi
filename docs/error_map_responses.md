# Error Map — `POST /v1/responses`

> Source: `app/routers/responses.py`

All non-streaming errors use the RouterV envelope:
```json
{"error": {"code": "<error_code>", "message": "..."}, "request_id": "req_..."}
```

**Exception:** HTTP 501 is raised via `HTTPException` directly (not `RouterVError`), so its response body follows FastAPI's default format: `{"detail": "..."}` — not the RouterV envelope.

Streaming errors follow the same SSE-frame pattern as `/v1/chat/completions` once HTTP 200 is committed.

---

## Error Table

| Endpoint | HTTP | `error_code` | Circumstance | Category |
|---|---|---|---|---|
| POST /v1/responses | 400 | `model_capability_not_supported` | `model_prices.supports_responses_api = false` for the resolved model+provider row | Platform |
| POST /v1/responses | 401 | `unauthorized` | `Authorization` header missing, malformed, or SHA-256 hash not found in Redis/DB | Platform |
| POST /v1/responses | 402 | `spend_limit_exceeded` | Key's `spend_cap_usd` already reached — `SUM(usage_events.cost_usd) >= cap` | Platform |
| POST /v1/responses | 402 | `spend_limit_exceeded` | Owner's `user_balances.balance_usd <= 0` for a paid model | Platform |
| POST /v1/responses | 403 | `forbidden` | API key exists in DB but `status != "active"` (suspended) | Platform |
| POST /v1/responses | 422 | `validation_error` | Pydantic request body validation failure | Platform |
| POST /v1/responses | 429 | `rate_limit_exceeded` | Fixed-window RPM or RPD Redis counter exceeds key's effective limit | Platform |
| POST /v1/responses | 429 | `rate_limit_exceeded` | Free-model RPM or RPD counter exceeded | Platform |
| POST /v1/responses | 500 | `upstream_error` | Upstream provider returned HTTP 4xx or 5xx on the `/responses` endpoint | Upstream Service |
| POST /v1/responses | 500 | `gateway_timeout` | `httpx.TimeoutException` — upstream did not respond within `timeout` seconds | Upstream Service |
| POST /v1/responses | 500 | `internal_error` | Unhandled `SQLAlchemyError` in `check_spend_cap`, `check_balance`, `resolve_routing`, or `db.get(ModelPrice)` | Platform |
| POST /v1/responses | 501 | _(FastAPI default format)_ | Resolved adapter class has not overridden `responses_create` or `stream_responses_create` — base no-op detected via `getattr` introspection | Platform |
| POST /v1/responses | 503 | `provider_not_available` | Provider slug in `model_prices.provider` has no registered adapter — required credentials absent from server environment | Platform |
| POST /v1/responses | 200 _(SSE error frame)_ | `upstream_error` / `gateway_timeout` | Exception raised inside streaming generator after HTTP 200 is committed; error delivered as SSE data frame | Upstream Service |

---

## Differences from `/v1/chat/completions`

| Aspect | chat/completions | responses |
|---|---|---|
| Template support | Yes — `template=` param resolves prompt template | No (deferred to V2) — no 404 from missing template |
| Capability flag | `supports_completions_api` | `supports_responses_api` |
| 501 path | Not present | Present — adapter introspection guard |
| Usage parsing | Needs `stream_options.include_usage=true` SSE injection | Responses API sends usage natively; no injection needed |

---

## Notes

- The 501 response body does **not** follow the RouterV error envelope — it is a raw FastAPI `HTTPException`. Clients should handle both shapes.
- Both `upstream_error` and `gateway_timeout` use **HTTP 500**. Inspect `error.code` to distinguish them.
