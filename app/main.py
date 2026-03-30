from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Header
from fastapi.exceptions import RequestValidationError

from app.cache.redis_client import close_redis, init_redis
from app.config import settings
from app.db.engine import close_db, init_db
from app.exceptions import RouterVError, routerv_exception_handler, validation_exception_handler
from app.logging_config import configure_logging
from app.middleware import CloudflareOriginGuard, RequestIdMiddleware
from app.providers.openrouter import OpenRouterAdapter
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import balance, inference, keys, models, payments, usage

from fastapi.middleware.cors import CORSMiddleware 

# Configure structlog before any logger is used.
configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", env=settings.env, version="0.1.0")

    # ── OpenRouter adapter ────────────────────────────────────────────────────
    OpenRouterAdapter.init(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        timeout=settings.openrouter_timeout_s,
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

    yield

    logger.info("shutdown")
    await OpenRouterAdapter.close()
    await close_db()
    await close_redis()


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
    # Order matters: middleware is applied last-registered-first (LIFO).
    # CloudflareOriginGuard must run BEFORE RequestIdMiddleware so blocked
    # requests never allocate a request ID or touch any handler logic.
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

    # Admin router: always registered, but gated differently per environment.
    # Dev  → no auth required (ENV guard is the protection)
    # Prod → requires Authorization: Bearer <ADMIN_SECRET> (must be set)
    from app.routers import admin
    app.include_router(admin.router)

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
