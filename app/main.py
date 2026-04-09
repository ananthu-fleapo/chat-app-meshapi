import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Header
from fastapi.exceptions import RequestValidationError

from app.cache.redis_client import close_redis, init_redis, get_redis
from app.config import settings
from app.db.engine import close_db, init_db, get_engine
from app.db.mongo import close_mongo, init_mongo
from app.exceptions import RouterVError, routerv_exception_handler, validation_exception_handler
from app.logging_config import configure_logging
from app.middleware import CloudflareOriginGuard, RequestIdMiddleware, RequestLoggingMiddleware
from app.metrics import update_pool_metrics, update_redis_metrics, PROCESS_CPU_CORES, PROCESS_TOTAL_MEMORY_BYTES
from app.providers.openrouter import OpenRouterAdapter
from app.providers.registry import register_adapter
from prometheus_fastapi_instrumentator import Instrumentator
import asyncio

from app.routers import auth, balance, inference, keys, models, payments, usage, fx_rates, gstin, admin, error_logs

from fastapi.middleware.cors import CORSMiddleware 

# Configure structlog before any logger is used.
configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", env=settings.env, version="0.1.0")

    # ── System resources ──────────────────────────────────────────────────────
    PROCESS_CPU_CORES.set(os.cpu_count() or 1)
    try:
        import psutil
        PROCESS_TOTAL_MEMORY_BYTES.set(psutil.virtual_memory().total)
    except ImportError:
        # psutil not available; use 512 MB fallback
        PROCESS_TOTAL_MEMORY_BYTES.set(512 * 1024 * 1024)

    # ── OpenRouter adapter ────────────────────────────────────────────────────
    OpenRouterAdapter.init(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        timeout=settings.openrouter_timeout_s,
    )

    # ── Vertex AI adapter (optional) ──────────────────────────────────────────
    # Enabled only when project_id + service account JSON are both configured.
    if settings.vertex_ai_project_id and settings.vertex_ai_service_account_json:
        from app.providers.vertex_ai import VertexAIAdapter
        VertexAIAdapter.init(
            project_id=settings.vertex_ai_project_id,
            location=settings.vertex_ai_location,
            service_account_json=settings.vertex_ai_service_account_json,
            timeout=settings.vertex_ai_timeout_s,
        )
        register_adapter("vertex", VertexAIAdapter)
    else:
        logger.info(
            "vertex_ai_adapter_skipped",
            hint="Set VERTEX_AI_PROJECT_ID and VERTEX_AI_SERVICE_ACCOUNT_JSON to enable",
        )

    # ── AWS Bedrock adapter (optional) ────────────────────────────────────────
    # Enabled if either a bearer API key or IAM credentials are configured.
    if settings.bedrock_api_key or (settings.aws_access_key_id and settings.aws_secret_access_key):
        from app.providers.bedrock import BedrockAdapter
        BedrockAdapter.init(
            region=settings.aws_region,
            timeout=settings.bedrock_timeout_s,
            api_key=settings.bedrock_api_key,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        register_adapter("bedrock", BedrockAdapter)
    else:
        logger.info(
            "bedrock_adapter_skipped",
            hint="Set BEDROCK_API_KEY (bearer) or AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (SigV4)",
        )

    # ── OpenAI Direct adapter (optional) ──────────────────────────────────────
    if settings.openai_api_key:
        from app.providers.openai_direct import OpenAIDirectAdapter
        OpenAIDirectAdapter.init(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.openai_timeout_s,
        )
        register_adapter("openai", OpenAIDirectAdapter)
    else:
        logger.info(
            "openai_direct_adapter_skipped",
            hint="Set OPENAI_API_KEY to enable direct OpenAI routing",
        )

    # ── Qwen / DashScope adapter (optional) ───────────────────────────────────
    if settings.qwen_api_key:
        from app.providers.qwen import QwenAdapter
        QwenAdapter.init(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            timeout=settings.qwen_timeout_s,
        )
        register_adapter("qwen", QwenAdapter)
    else:
        logger.info(
            "qwen_adapter_skipped",
            hint="Set QWEN_API_KEY to enable direct Qwen/DashScope routing",
        )

    # ── Required secrets check ────────────────────────────────────────────────
    # Fail fast rather than starting in a broken state where all control-plane
    # auth silently falls back to the insecure dev bypass.
    if not settings.supabase_jwt_secret:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET is not set. "
            "Set it to the JWT secret from Supabase → Settings → API → JWT Secret."
        )

    # ── Database ──────────────────────────────────────────────────────────────
    if settings.database_url:
        init_db(settings.database_url, echo=(settings.env == "dev"))
        logger.info("db_ready")
    else:
        logger.warning("db_not_configured", hint="Set DATABASE_URL in .env")

    # ── Redis ─────────────────────────────────────────────────────────────────
    # Provides key-lookup cache + cross-instance rate limiting.
    # Fails fast at startup if REDIS_URL is set but unreachable.
    if settings.redis_url:
        await init_redis(settings.redis_url)
    else:
        logger.warning("redis_not_configured", hint="Set REDIS_URL in .env")

    # ── MongoDB ───────────────────────────────────────────────────────────────
    # Stores request_logs (all HTTP traffic) and usage_events (dual-write with
    # Postgres). Optional — app runs fine without it, logging falls back to
    # Postgres-only + structured logs.
    if settings.mongodb_url:
        try:
            await init_mongo(settings.mongodb_url, settings.mongodb_database)
        except Exception as exc:  # noqa: BLE001
            # MONGODB_URL is explicitly configured — fail fast rather than starting
            # silently broken. Operators must fix connectivity before serving traffic.
            logger.error(
                "mongo_connect_failed",
                error=str(exc),
                mongodb_url=settings.mongodb_url,
            )
            raise
    else:
        logger.warning("mongo_not_configured", hint="Set MONGODB_URL in .env to enable MongoDB logging")

    # ── Background metrics task ───────────────────────────────────────────────
    # Update DB pool and Redis metrics every 10 seconds.
    async def update_metrics_loop():
        while True:
            try:
                engine = get_engine()
                if engine:
                    update_pool_metrics(engine)
                redis = get_redis()
                if redis:
                    await update_redis_metrics(redis)
            except Exception as e:
                logger.warning("metrics_update_failed", error=str(e))
            await asyncio.sleep(10)

    metrics_task = asyncio.create_task(update_metrics_loop())

    yield

    metrics_task.cancel()
    try:
        await metrics_task
    except asyncio.CancelledError:
        pass

    logger.info("shutdown")
    await OpenRouterAdapter.close()

    # Close optional adapters if they were initialised
    from app.providers.registry import _REGISTRY
    if "vertex" in _REGISTRY:
        from app.providers.vertex_ai import VertexAIAdapter
        await VertexAIAdapter.close()
    if "bedrock" in _REGISTRY:
        from app.providers.bedrock import BedrockAdapter
        await BedrockAdapter.close()
    if "openai" in _REGISTRY:
        from app.providers.openai_direct import OpenAIDirectAdapter
        await OpenAIDirectAdapter.close()
    if "qwen" in _REGISTRY:
        from app.providers.qwen import QwenAdapter
        await QwenAdapter.close()

    await close_db()
    await close_redis()
    await close_mongo()


def create_app() -> FastAPI:
    app = FastAPI(
        title="RouterV",
        version="0.1.0",
        description="One key, all AI models.",
        lifespan=lifespan,
        # Disable interactive docs in prod — avoids leaking schema info.
        docs_url="/docs" if settings.env == "dev" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.env == "dev" else None,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    # Execution order for incoming requests (LIFO — last added runs outermost):
    #   CORSMiddleware → CloudflareOriginGuard → RequestIdMiddleware
    #     → RequestLoggingMiddleware → route handler
    #
    # RequestLoggingMiddleware is innermost so it sees the request_id and owner
    # already set in scope["state"] by RequestIdMiddleware and the auth dep.
    # It is a raw ASGI class (not BaseHTTPMiddleware) so streaming is unaffected.
    app.add_middleware(RequestLoggingMiddleware)  # innermost — added first
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(CloudflareOriginGuard)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        # allow_credentials requires explicit origins — cannot be used with "*"
        allow_credentials=settings.cors_origins != "*",
        allow_methods=["*"],
        allow_headers=["*"],
    )                       


    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(RouterVError, routerv_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(auth.router)
    app.include_router(inference.router)
    app.include_router(keys.router)
    app.include_router(balance.router)
    app.include_router(usage.router)
    app.include_router(payments.router)

    # Template management: production endpoint, auth-gated, owner-scoped.
    from app.routers import templates
    app.include_router(templates.router)

    # NOTE: /v1/provider-keys is intentionally NOT registered here.
    # Provider key management is operator-only — handled via /admin/provider-keys
    # (dev-only admin router below).  RouterV users never see or manage the
    # upstream keys that back their requests.

    # Models listing: unauthenticated, public info.
    app.include_router(models.router)

    # FX rate refresh: internal scheduler endpoint, guarded by WEBHOOK_API_KEY.
    app.include_router(fx_rates.router)

    # Model health check: Cloud Scheduler endpoint, guarded by WEBHOOK_API_KEY.
    from app.routers import model_health
    app.include_router(model_health.router)

    # GSTIN verification: user-authenticated, results cached 6 months in Redis.
    app.include_router(gstin.router)

    # Admin router: JWT-gated. Caller must have app_metadata.permissions
    # containing "mesh_api:admin".
    app.include_router(admin.router)
    app.include_router(error_logs.router)

    # ── Prometheus metrics ────────────────────────────────────────────────────
    # Instruments HTTP metrics. Endpoint is registered manually below so we
    # can gate it behind a bearer token for Grafana Cloud scraping.
    Instrumentator(excluded_handlers=["/metrics", "/healthz", "/readyz"]).instrument(app)

    @app.get("/metrics", include_in_schema=False)
    async def metrics(authorization: str = Header(default="")):
        """
        Prometheus metrics endpoint.
        Requires: Authorization: Bearer <METRICS_TOKEN> when METRICS_TOKEN is set.
        Configure this token in the Grafana Cloud scrape job.
        """
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        if settings.metrics_token:
            if authorization != f"Bearer {settings.metrics_token}":
                from fastapi.responses import Response as FR
                return FR(
                    content='{"error":{"code":"unauthorized","message":"Invalid metrics token."}}',
                    status_code=401,
                    media_type="application/json",
                )

        from fastapi.responses import Response as FR
        return FR(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # ── Utility endpoints ─────────────────────────────────────────────────────
    @app.get("/healthz", include_in_schema=False)
    async def health():
        """
        Liveness probe.
        Cloud Run and GKE use this to verify the container is alive.
        Returns 200 as soon as the app is ready to serve traffic.
        This endpoint intentionally does NOT check DB/Redis — it must
        succeed even if backing services are temporarily unreachable.
        """
        return {"status": "ok", "env": settings.env}

    @app.get("/readyz", include_in_schema=False)
    async def readiness():
        """
        Readiness probe.
        Returns 200 only when the app can actually serve traffic:
        - Postgres is reachable (simple SELECT 1)
        - Redis is reachable (PING)

        Cloud Run / GKE uses this to gate traffic routing.
        Until readyz returns 200, the instance receives no traffic.
        """
        from app.cache.redis_client import get_redis
        from app.db.engine import get_engine
        import sqlalchemy as sa

        checks: dict[str, str] = {}
        ok = True

        # ── Postgres ──────────────────────────────────────────────────────────
        try:
            engine = get_engine()
            if engine is not None:
                async with engine.connect() as conn:
                    await conn.execute(sa.text("SELECT 1"))
                checks["postgres"] = "ok"
            else:
                checks["postgres"] = "not_configured"
        except Exception as exc:  # noqa: BLE001
            checks["postgres"] = f"error: {exc}"
            ok = False

        # ── Redis ─────────────────────────────────────────────────────────────
        try:
            redis = get_redis()
            if redis is not None:
                await redis.ping()
                checks["redis"] = "ok"
            else:
                checks["redis"] = "not_configured"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"error: {exc}"
            ok = False

        if not ok:
            from fastapi import Response
            return Response(
                content=str({"status": "degraded", "checks": checks}),
                status_code=503,
                media_type="application/json",
            )

        return {"status": "ok", "checks": checks}

    return app


app = create_app()
