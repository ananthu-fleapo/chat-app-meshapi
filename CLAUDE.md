# RouterSVC — Claude Context

## Project Overview

**RouterSVC** is an OpenAI-compatible AI model gateway built on FastAPI, proxying requests to [OpenRouter](https://openrouter.ai). It provides:

- Multi-tenant API key management (`rsk_<ULID>` keys, SHA-256 hash stored)
- Per-owner rate limiting (RPM/RPD via Redis fixed-window counters)
- Per-key spend caps and credit balance enforcement
- Usage tracking and billing (per-request token/cost logging)
- Prompt template system (`{{variable}}` substitution)
- Per-owner upstream provider key provisioning (via OpenRouter management API + GCP Secret Manager)
- GCP-native deployment: Cloud Run, Cloud SQL (PostgreSQL), Memorystore (Redis), Secret Manager, Cloud Build

---

## Tech Stack

| Layer | Tech |
|---|---|
| Language | Python 3.12+ |
| Framework | FastAPI 0.115+ |
| Database | PostgreSQL 16 (asyncpg + SQLAlchemy async) |
| Migrations | Alembic 1.13+ |
| Cache / Rate Limiting | Redis 7 (asyncio) |
| HTTP Client | httpx 0.27+ |
| Validation | Pydantic 2.7+ / pydantic-settings 2.3+ |
| Logging | structlog 24.2+ (GCP Cloud Logging JSON in prod) |
| Metrics | Prometheus + prometheus-fastapi-instrumentator 7.0+ |
| Auth | PyJWT 2.9+ (HS256 Supabase tokens) |
| IDs | python-ulid 2.7+ |
| Secrets | GCP Secret Manager (`[gcp]` extras) |
| Testing | pytest 8.2+ + pytest-asyncio 0.23+ |

---

## Local Dev Commands

```bash
# Setup
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"           # add [gcp] for Secret Manager support

# Infra (PostgreSQL 16 + Redis 7)
docker-compose up -d

# DB migrations
alembic upgrade head

# Run server
uvicorn app.main:app --reload --port 8000

# With monitoring (Prometheus :9090, Grafana :3000 admin/admin)
docker-compose --profile monitoring up -d
```

### Tests

```bash
pytest                              # all tests
pytest tests/test_rate_limiter.py   # single file
pytest -k "rate_limit" -v           # filter by name
```

---

## Environment Variables

Copy `.env.example` to `.env`. Key vars:

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

## Architecture Map

```
app/
  routers/          FastAPI endpoints (inference, keys, balance, usage, templates, payments, models, admin)
  auth/             JWT verification, API key lookup, dependency injection
  providers/        OpenRouter client, per-owner key resolver, provisioner, Secret Manager
  cache/            Redis key cache, fixed-window RPM/RPD rate limiter
  db/               SQLAlchemy async models, engine, session factory
  usage/            Usage logging, balance checks, pricing rules, spend caps
  templates/        {{variable}} prompt template renderer and resolver
  config.py         Pydantic settings (all env vars)
  main.py           FastAPI app factory + lifespan
  middleware.py     RequestIdMiddleware, CloudflareOriginGuard
  exceptions.py     Custom error hierarchy + FastAPI handlers
  metrics.py        Prometheus helpers

alembic/versions/   10 migrations (0001 api_keys → 0010 model_prices/user_balances)
tests/              pytest unit tests (mock DB via AsyncMock, env vars set before import)
```

### Database Tables

| Table | Purpose |
|---|---|
| `api_keys` | RouterSVC-issued keys (hash stored, plaintext returned once) |
| `templates` | Per-owner prompt templates with `{{variable}}` slots |
| `usage_events` | Per-request logs: model, tokens, cost_usd, latency_ms |
| `provider_keys` | Per-owner upstream key references (GCP Secret Manager) |
| `payment_events` | Payment/billing event log |
| `model_prices` | Per-model input/output token pricing (USD) |
| `user_balances` | Credit balance per owner |

---

## Request Lifecycle (Inference)

```
POST /v1/chat/completions
  → CloudflareOriginGuard      validates X-Origin-Secret (prod)
  → RequestIdMiddleware         assigns req_<ULID>, binds trace context
  → get_authenticated_key()     SHA-256 lookup, status check
  → check_rate_limits()         Redis RPM/RPD fixed-window
  → check_spend_cap()           402 if over limit
  → resolve_template()          DB lookup + {{var}} render (if template= set)
  → resolve_config()            merge request params with key.default_params
  → check_balance()             owner credit check
  → resolve_upstream_key()      system key or per-owner from Secret Manager
  → OpenRouterAdapter           proxy to OpenRouter (streaming or JSON)
  → fire_usage_log()            async DB write (tokens, cost, latency)
  → return response
```

---

## CI/CD Pipeline (`cloudbuild.yaml`)

5-step Cloud Build triggered on push to `main`:

1. **Build** — multi-stage Docker image (non-root UID 1001), layer-cached via `:latest`
2. **Push** — to Artifact Registry (`:SHORT_SHA` + `:latest` tags)
3. **Create migration job** — `gcloud run jobs create` (delete-then-recreate pattern)
4. **Run migration** — `gcloud run jobs execute --wait` (Alembic `upgrade head`)
5. **Deploy + shift traffic** — `gcloud run services update --no-traffic` then `update-traffic --to-latest`

### Key CI constraints

- `_DATABASE_URL` must be set in the Cloud Build **trigger** substitutions (not the yaml default)
- `_SERVICE_ACCOUNT` = `api-routersvc-sa@fair-myth-471110-j2.iam.gserviceaccount.com`
- Migration job must pass `--service-account=_SERVICE_ACCOUNT` (default compute SA lacks Cloud SQL access)
- `openrouter_api_key` has `= ""` default in `config.py` — pydantic validates all settings on import; migration job has no OpenRouter key set

---

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "short_description"

# Apply
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

Alembic env (`alembic/env.py`) reads `DATABASE_URL` from the environment and uses the async engine.

---

## Known Pitfalls

- **`openrouter_api_key` default** — must be `= ""` not required. Pydantic validates settings at import time; migration Cloud Run jobs don't have the key in env, causing startup failure.
- **Migration job service account** — must explicitly pass `--service-account=api-routersvc-sa@...`; the default compute SA doesn't have Cloud SQL Client or Secret Manager roles.
- **`DATABASE_URL` as env var, not secret** — Cloud Run jobs don't support `--update-secrets` inline refs the same way services do; pass as `--set-env-vars`.
- **structlog context** — bind per-request via `structlog.contextvars.bind_contextvars()`; don't use module-level loggers directly or context won't propagate.
- **Test env vars** — must be set BEFORE importing app modules. `conftest.py` sets them at module load time; pydantic-settings reads env at class definition.
- **Rate limiter expiry** — Redis keys auto-expire; no manual cleanup needed.
- **Streaming usage logging** — `fire_usage_log()` fires after the stream completes (SSE parsing detects final chunk); don't log before stream is done.

---

## Monitoring & Health

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness — instant 200, no DB/Redis checks |
| `GET /readyz` | Readiness — Postgres `SELECT 1` + Redis `PING`; 503 if either fails |
| `GET /metrics` | Prometheus metrics (requires `METRICS_TOKEN` bearer) |

Local monitoring stack: `docker-compose --profile monitoring up -d`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (admin / admin)
