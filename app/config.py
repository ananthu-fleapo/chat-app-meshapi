from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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
    default_rpd: int = 5000

    # Hard ceiling — effective limits are clamped to these values regardless
    # of per-key overrides.  Admin cannot set a key above these values.
    max_rpm: int = 100
    max_rpd: int = 7500

    # Separate, tighter limits applied only to free-model requests.
    # Counted on a separate Redis key (shared across all free models per key)
    # so a user cannot get unlimited free usage by rotating models.
    default_free_rpm: int = 20
    default_free_rpd: int = 200

    # ── Vertex AI ─────────────────────────────────────────────────────────────
    # Set these to route models to Vertex AI.
    # vertex_ai_service_account_json: full JSON string of a service account key,
    #   typically injected from a GCP Secret or environment variable.
    # Leave all empty to disable Vertex AI routing.
    vertex_ai_project_id: str = ""
    vertex_ai_location: str = "us-central1"
    vertex_ai_service_account_json: str = ""  # full JSON string
    vertex_ai_timeout_s: float = 120.0

    # ── AWS Bedrock ───────────────────────────────────────────────────────────
    # Two auth modes (set one):
    #   Bearer token  — bedrock_api_key (long-term key from Bedrock console → API keys)
    #                   Uses httpx; simpler, no IAM needed.
    #   SigV4/IAM     — aws_access_key_id + aws_secret_access_key
    #                   Uses aiobotocore; required for cross-account or fine-grained IAM.
    # bedrock_api_key takes priority when both are set.
    bedrock_api_key: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    bedrock_timeout_s: float = 120.0

    # ── OpenAI Direct ─────────────────────────────────────────────────────────
    # Set openai_api_key to route models directly to OpenAI (bypassing OpenRouter).
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout_s: float = 120.0

    # ── Qwen / DashScope ──────────────────────────────────────────────────────
    # Set qwen_api_key to route Qwen models via Alibaba Cloud DashScope API.
    # DashScope exposes an OpenAI-compatible endpoint.
    # Use the international endpoint if your key is from modelstudio.console.alibabacloud.com:
    #   https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    # Use the China endpoint if your key is from dashscope.console.aliyun.com:
    #   https://dashscope.aliyuncs.com/compatible-mode/v1
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_timeout_s: float = 120.0

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
    # Supabase anon key — used by the backend to call Supabase Auth REST API
    # (send OTP, verify OTP). Find it at Supabase → Settings → API → anon key.
    supabase_anon_key: str = ""
    # Which JWT claim to use as the RouterV owner label.
    # Checked in order: user_metadata.<claim>, app_metadata.<claim>, <claim>.
    # Falls back to `sub` (Supabase user UUID) when unset or claim not found.
    # Example: set to "routerv_owner" and add that field to Supabase user_metadata.
    supabase_owner_claim: str = ""

    # ── FX rate refresh ───────────────────────────────────────────────────────
    # URL for the exchange rate API called by POST /internal/fx-rates/refresh.
    exchange_rate_api_url: str = ""

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
