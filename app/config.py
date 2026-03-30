from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Environment ───────────────────────────────────────────────────────────
    # "dev"  → pretty console logs, /docs enabled, DEBUG-friendly
    # "prod" → JSON logs in GCP Cloud Logging format, /docs disabled
    env: Literal["dev", "prod"] = "dev"
    log_level: str = "INFO"

    # ── Server ────────────────────────────────────────────────────────────────
    # Cloud Run injects PORT; locally defaults to 8000.
    port: int = 8000

    # ── OpenRouter ────────────────────────────────────────────────────────────
    # Default system key — used when no per-owner provider key is configured.
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_s: float = 120.0
    # Management key — separate credential used ONLY for provisioning per-owner
    # keys via the OpenRouter key management API. Cannot be used for completions.
    # Create at: https://openrouter.ai/settings/management-keys
    # Leave empty to disable auto-provisioning (keys fall back to system default).
    openrouter_management_key: str = ""

    # ── Database (Phase 2) ────────────────────────────────────────────────────
    # Local:  postgresql+asyncpg://routersvc:routersvc@localhost:5432/routersvc
    # GCP:    postgresql+asyncpg://user:pass@/db?host=/cloudsql/project:region:instance
    database_url: str = ""

    # ── Redis (Phase 3) ───────────────────────────────────────────────────────
    # Local:  redis://localhost:6379/0
    # GCP:    redis://10.x.x.x:6379/0  (Memorystore for Redis, private VPC IP)
    redis_url: str = "redis://localhost:6379/0"

    # ── Rate limiting defaults (Phase 3) ──────────────────────────────────────
    # Applied when a key has no explicit rpm_limit / rpd_limit set (NULL in DB).
    # Override per-key via PATCH /admin/keys/{id}.
    default_rpm: int = 60
    default_rpd: int = 1000

    # ── GCP (Phase 7+) ────────────────────────────────────────────────────────
    gcp_project_id: str = ""

    # ── Supabase / Control plane auth ────────────────────────────────────────
    # The JWT secret from Supabase → Settings → API → JWT Secret.
    # Used to verify HS256-signed JWTs on control plane endpoints (templates,
    # models listing). AuthN is Supabase's responsibility; we only verify sig.
    #
    # Leave empty in dev to bypass JWT verification (any token = accepted,
    # its raw value is used as the owner label for local testing).
    supabase_jwt_secret: str = ""
    # Your Supabase project URL: https://<project-ref>.supabase.co
    # Used to validate the `iss` claim. Optional but recommended in prod.
    supabase_url: str = ""
    # Which JWT claim to use as the RouterV owner label.
    # Checked in order: user_metadata.<claim>, app_metadata.<claim>, <claim>.
    # Falls back to `sub` (Supabase user UUID) when unset or claim not found.
    # Example: set to "routerv_owner" and add that field to Supabase user_metadata.
    supabase_owner_claim: str = ""

    # ── Webhook auth ─────────────────────────────────────────────────────────
    # Static secret for inbound webhook calls (e.g. payment provider callbacks).
    # Set WEBHOOK_API_KEY in .env. Requests must pass it as: Bearer <key>.
    # Leave empty in dev to disable the check.
    webhook_api_key: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins for browser requests.
    # Dev default "*" — in prod set to your exact frontend URL(s), e.g.:
    #   CORS_ORIGINS=https://app.yourdomain.com,https://yourdomain.com
    # Cannot use "*" when allow_credentials=True (CORS spec violation).
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Cloudflare origin guard ───────────────────────────────────────────────
    # When set, every inbound request must carry this value in X-Origin-Secret.
    # Cloudflare is configured to inject the header; direct hits to the Cloud
    # Run URL (bypassing Cloudflare) will be rejected with 403.
    # Leave empty in dev — the check is skipped when unset.
    cf_secret: str = ""

    # ── Metrics scrape auth ───────────────────────────────────────────────────
    # Bearer token required to scrape GET /metrics.
    # Set in Grafana Cloud scrape job as: Authorization: Bearer <token>
    # Leave empty in dev to allow unauthenticated scraping.
    metrics_token: str = ""


settings = Settings()
