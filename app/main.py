from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.cache.redis_client import close_redis, init_redis
from app.config import settings
from app.db.engine import close_db, init_db
from app.exceptions import RouterVError, routerv_exception_handler, validation_exception_handler
from app.logging_config import configure_logging
from app.middleware import RequestIdMiddleware
from app.providers.openrouter import OpenRouterAdapter
from app.routers import inference

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
    app.add_middleware(RequestIdMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(RouterVError, routerv_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(inference.router)

    # Template management: production endpoint, auth-gated, owner-scoped.
    from app.routers import templates
    app.include_router(templates.router)

    # Admin router: registered only in dev.
    # In prod, /admin/* routes simply don't exist → 404 from the framework.
    if settings.env == "dev":
        from app.routers import admin
        app.include_router(admin.router)

    # ── Utility endpoints ─────────────────────────────────────────────────────
    @app.get("/healthz", include_in_schema=False)
    async def health():
        """
        Liveness probe.
        Cloud Run and GKE use this to verify the container is alive.
        Returns 200 as soon as the app is ready to serve traffic.
        """
        return {"status": "ok", "env": settings.env}

    return app


app = create_app()
