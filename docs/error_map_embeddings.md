# Error Map — `POST /v1/embeddings`

> Source: `app/routers/embeddings.py`

All errors use the RouterV envelope:
```json
{"error": {"code": "<error_code>", "message": "..."}, "request_id": "req_..."}
```

---

## Error Table

| Endpoint | HTTP | `error_code` | Circumstance | Category |
|---|---|---|---|---|
| POST /v1/embeddings | 401 | `unauthorized` | `Authorization` header missing, malformed, or SHA-256 hash not found in Redis/DB | Platform |
| POST /v1/embeddings | 402 | `spend_limit_exceeded` | Key's `spend_cap_usd` already reached — `SUM(usage_events.cost_usd) >= cap` | Platform |
| POST /v1/embeddings | 402 | `spend_limit_exceeded` | Owner's `user_balances.balance_usd <= 0` for a paid embedding model | Platform |
| POST /v1/embeddings | 403 | `forbidden` | API key exists in DB but `status != "active"` (suspended) | Platform |
| POST /v1/embeddings | 422 | `validation_error` | Pydantic request body validation failure (e.g. missing `model` or `input` field) | Platform |
| POST /v1/embeddings | 429 | `rate_limit_exceeded` | Fixed-window RPM Redis counter exceeds key's effective RPM limit | Platform |
| POST /v1/embeddings | 429 | `rate_limit_exceeded` | Fixed-window RPD Redis counter exceeds key's effective RPD limit | Platform |
| POST /v1/embeddings | 429 | `rate_limit_exceeded` | Free-model RPM or RPD counter exceeded (if embedding model is free-tier) | Platform |
| POST /v1/embeddings | 500 | `upstream_error` | Upstream provider returned HTTP 4xx or 5xx on the `/embeddings` endpoint | Upstream Service |
| POST /v1/embeddings | 500 | `gateway_timeout` | `httpx.TimeoutException` — upstream did not respond within `timeout` seconds | Upstream Service |
| POST /v1/embeddings | 500 | `internal_error` | Unhandled `SQLAlchemyError` in `check_spend_cap`, `check_balance`, or `resolve_routing` | Platform |
| POST /v1/embeddings | 503 | `provider_not_available` | Provider slug in `model_prices.provider` has no registered adapter — required credentials absent from server environment | Platform |

---

## Differences from `/v1/chat/completions`

| Aspect | chat/completions | embeddings |
|---|---|---|
| Template support | Yes | No |
| Capability guard | `supports_completions_api` check present | **No** capability guard — missing `supports_embeddings_api` check |
| Streaming | Yes (SSE) | No — always synchronous JSON response |
| SSE error frame path | Present | Not applicable |

---

## Notes

- The embeddings router does **not** check a `supports_embeddings_api` flag. A model configured as a completions-only model in `model_prices` will still be attempted for embeddings; the error will come back as a 500 `upstream_error` from the provider.
- Both `upstream_error` and `gateway_timeout` use **HTTP 500**. Inspect `error.code` to distinguish them.
- Redis unavailability in the rate limiter fails **open** — request is allowed through with a `WARNING` log.
