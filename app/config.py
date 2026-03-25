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
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_s: float = 120.0

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


settings = Settings()
