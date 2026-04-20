# Error Map — `POST /v1/chat/completions`

> Source: `app/routers/inference.py`

All non-streaming errors use the RouterV envelope:
```json
{"error": {"code": "<error_code>", "message": "..."}, "request_id": "req_..."}
```

Streaming errors (once HTTP 200 and `text/event-stream` headers are already committed) are delivered
as an SSE data frame: `data: {"error": {"code": "...", "message": "..."}}\n\ndata: [DONE]\n\n`

---

## Error Table

| Endpoint | HTTP | `error_code` | Circumstance | Category |
|---|---|---|---|---|
| POST /v1/chat/completions | 400 | `model_capability_not_supported` | `model_prices.supports_completions_api = false` for the resolved model+provider row | Platform |
| POST /v1/chat/completions | 401 | `unauthorized` | `Authorization` header missing, malformed, or SHA-256 hash not found in Redis/DB | Platform |
| POST /v1/chat/completions | 402 | `spend_limit_exceeded` | Key's `spend_cap_usd` already reached — `SUM(usage_events.cost_usd) >= cap` | Platform |
| POST /v1/chat/completions | 402 | `spend_limit_exceeded` | Owner's `user_balances.balance_usd <= 0` for a paid model | Platform |
| POST /v1/chat/completions | 403 | `forbidden` | API key exists in DB but `status != "active"` (suspended) | Platform |
| POST /v1/chat/completions | 404 | `not_found` | `template=` param set but template UUID not found in DB for this owner | Platform |
| POST /v1/chat/completions | 422 | `validation_error` | Pydantic request body validation failure (e.g. missing `model`, bad field type) | Platform |
| POST /v1/chat/completions | 429 | `rate_limit_exceeded` | Fixed-window RPM Redis counter exceeds key's effective RPM limit | Platform |
| POST /v1/chat/completions | 429 | `rate_limit_exceeded` | Fixed-window RPD Redis counter exceeds key's effective RPD limit | Platform |
| POST /v1/chat/completions | 429 | `rate_limit_exceeded` | Free-model RPM or RPD counter exceeded (separate Redis namespace) | Platform |
| POST /v1/chat/completions | 500 | `upstream_error` | Upstream provider (OpenRouter, Bedrock, Vertex, OpenAI, Qwen) returned HTTP 4xx or 5xx | Upstream Service |
| POST /v1/chat/completions | 500 | `gateway_timeout` | `httpx.TimeoutException` — upstream did not respond within the configured `timeout` seconds | Upstream Service |
| POST /v1/chat/completions | 500 | `internal_error` | Unhandled `SQLAlchemyError` in `check_spend_cap`, `check_balance`, `resolve_routing`, or the `db.get(ModelPrice)` capability check | Platform |
| POST /v1/chat/completions | 503 | `provider_not_available` | Provider slug stored in `model_prices.provider` has no registered adapter — the required credentials (e.g. `VERTEX_AI_PROJECT_ID`) are absent from the server environment | Platform |
| POST /v1/chat/completions | 200 _(SSE error frame)_ | `upstream_error` / `gateway_timeout` | Any exception raised inside the streaming generator after HTTP 200 is committed; error is embedded in the SSE stream, not the HTTP status | Upstream Service |

---

## Notes

- **Redis unavailability** (rate limiter): `check_rate_limits` and `check_free_model_rate_limits` fail **open** — the request is allowed through and a `WARNING` is logged. No error is returned to the caller.
- **Secret Manager unavailability** (`resolve_upstream_key`): silently falls back to the system-default API key and logs a `WARNING`. No error is returned.
- **`_get_models()` DB failure**: caught internally, returns an empty list — never surfaces as a 500 to the caller.
- Both `upstream_error` and `gateway_timeout` currently use **HTTP 500**. Clients should inspect `error.code` to distinguish a provider error from a timeout.
