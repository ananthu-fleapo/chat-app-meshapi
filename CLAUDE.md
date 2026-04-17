# MeshAPI — Backend (`backend/`)

**MeshAPI** is a multi-tenant, OpenAI-compatible AI model gateway built on FastAPI. It proxies inference requests to upstream providers (OpenRouter, Vertex AI, Bedrock, OpenAI, Qwen) while enforcing per-key rate limits, spend caps, credit balances, and prompt templates — giving teams a single API surface with full usage tracking and billing.

```bash
cd backend

# Setup
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"           # add [gcp] for Secret Manager support

# Infra (PostgreSQL 16 + Redis 7)
docker-compose up -d

# DB migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
alembic downgrade -1

# Run server
uvicorn app.main:app --reload --port 8000

# Tests
pytest
pytest tests/test_rate_limiter.py         # single file
pytest tests/test_balance.py::test_fn -v  # single test
pytest -k "rate_limit" -v                 # filter by name

# With monitoring (Prometheus :9090, Grafana :3000 admin/admin)
docker-compose --profile monitoring up -d
```

---

## Architecture

Multi-tenant API gateway with three auth planes:

- **Data plane** — `Authorization: Bearer rsk_<ULID>` (SHA-256 hash stored in DB)
- **Control plane** — Supabase JWT tokens (dashboard/management routes)
- **Admin plane** — `/admin/*` (no auth when `SUPABASE_JWT_SECRET` unset)

**Inference request flow:**
```
POST /v1/chat/completions
  → CloudflareOriginGuard      (X-Origin-Secret, prod only)
  → RequestIdMiddleware         (req_<ULID>, structlog context)
  → get_authenticated_key()     (SHA-256 lookup, Redis cache → DB)
  → check_rate_limits()         (Redis fixed-window RPM/RPD)
  → check_spend_cap()           (402 if over limit)
  → resolve_template()          (DB + {{var}} render)
  → resolve_config()            (merge request → key defaults → template defaults)
  → check_balance()             (owner credit check)
  → resolve_upstream_key()      (system key or per-owner from GCP Secret Manager)
  → provider adapter            (OpenRouter / Vertex / Bedrock / OpenAI / Qwen)
  → fire_usage_log()            (async DB write: tokens, cost, latency)
```

**Key modules:**

| Module | Purpose |
|---|---|
| `app/routers/inference.py` | Core LLM proxy |
| `app/providers/openrouter.py` | `OpenRouterAdapter` — singleton httpx client, SSE parsing |
| `app/auth/config_resolver.py` | Merges request params with per-key and template defaults |
| `app/cache/rate_limiter.py` | Fixed-window RPM/RPD counters in Redis |
| `app/usage/spend_cap.py` | Per-key USD spend cap enforcement (402) |
| `app/middleware.py` | Cloudflare origin guard + ULID request ID |
| `app/config.py` | All config via Pydantic Settings from `.env` |

**Provider routing** — DB-driven via `model_prices.provider`:

| Provider | Slug | Auth |
|---|---|---|
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` (default) |
| Vertex AI | `vertex` | Service account JSON |
| AWS Bedrock | `bedrock` | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| OpenAI Direct | `openai` | `OPENAI_API_KEY` |
| Qwen / DashScope | `qwen` | `QWEN_API_KEY` |

**Dev bypasses** (when env vars are unset): No `DATABASE_URL` → DB skipped; No `REDIS_URL` → rate limiting skipped; No `SUPABASE_JWT_SECRET` → any token accepted as owner ID; No `CF_SECRET` → origin guard disabled.

**Known pitfalls:**
- `openrouter_api_key` must default to `= ""` in `config.py` — Pydantic validates at import time; migration jobs don't have this key set
- Test env vars must be set BEFORE importing app modules (`conftest.py` handles this)
- structlog context: bind per-request via `structlog.contextvars.bind_contextvars()`; don't use module-level loggers directly
- Streaming usage logging fires after stream completes (SSE final chunk), not before
- `GET /v1/models` is DB-only (no upstream calls); Redis cache 5-min TTL, invalidated on any admin write

---

## Environment Variables

Copy `.env.example` to `.env`:

| Var | Required | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | Prod | System-default LLM key; defaults to `""` so migrations don't fail on import |
| `DATABASE_URL` | Prod | `postgresql+asyncpg://user:pass@/db?host=/cloudsql/...` |
| `REDIS_URL` | Prod | `redis://10.x.x.x:6379/0` |
| `SUPABASE_JWT_SECRET` | Prod | Empty in dev → any token accepted as owner label |
| `CF_SECRET` | Prod | Cloudflare origin guard; empty = disabled |
| `OPENROUTER_MANAGEMENT_KEY` | Optional | Auto-provisions per-owner keys |
| `WEBHOOK_API_KEY` | Optional | Static bearer for inbound webhooks |
| `METRICS_TOKEN` | Optional | Bearer for `/metrics` endpoint |
| `GCP_PROJECT_ID` | Optional | Required for Secret Manager |

---

## Database Tables

| Table | Purpose |
|---|---|
| `api_keys` | RouterSVC-issued keys (hash stored, plaintext returned once) |
| `templates` | Per-owner prompt templates with `{{variable}}` slots |
| `usage_events` | Per-request logs: model, tokens, cost_usd, latency_ms |
| `provider_keys` | Per-owner upstream key references (GCP Secret Manager) |
| `payment_events` | Payment/billing event log |
| `models` | Model registry whitelist — name, context_length, description, is_enabled |
| `model_prices` | Per-model per-provider pricing (composite PK: model_id + provider) |
| `user_balances` | Credit balance per owner |
| `discounts` | Per-user/per-model discount percentages |
| `currency_conversion_rates` | FX rates to USD with markup |

`GET /v1/models` is **DB-only** — joins `models` + `model_prices` (is_default=true, is_enabled=true); Redis cache 5-min TTL, invalidated on any admin write.

---

## CI/CD (`cloudbuild.yaml`)

Cloud Build triggered on push to `main`:

1. **Build** — multi-stage Docker image (non-root UID 1001) → Artifact Registry (`:SHORT_SHA` + `:latest`)
2. **Migrate** — recreate Cloud Run job → `alembic upgrade head`
3. **Deploy** — `gcloud run services update --no-traffic` then shift traffic to latest

**Constraints:**
- `_DATABASE_URL` must be set in Cloud Build trigger substitutions (not the yaml default)
- Migration job must pass `--service-account=api-routersvc-sa@...` (default compute SA lacks Cloud SQL access)
- `DATABASE_URL` passed as env var (not secret) for Cloud Run jobs

---

## Monitoring

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness — instant 200, no DB/Redis checks |
| `GET /readyz` | Readiness — Postgres `SELECT 1` + Redis `PING`; 503 if either fails |
| `GET /metrics` | Prometheus metrics (requires `METRICS_TOKEN` bearer) |

Local stack: `docker-compose --profile monitoring up -d` → Prometheus `:9090`, Grafana `:3000` (admin/admin)
