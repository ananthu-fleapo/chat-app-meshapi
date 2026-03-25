"""
Async SQLAlchemy engine + session factory.

Lifecycle
---------
init_db()   called once in app lifespan (startup).
close_db()  called once in app lifespan (shutdown).

Both are synchronous to call (they manage internal async objects).
The engine and session factory are module-level singletons — there is
exactly one connection pool for the entire process.

GCP production note
-------------------
Cloud Run connects to Cloud SQL via a Unix socket injected by the
Cloud SQL Auth Proxy sidecar:

  DATABASE_URL=postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE

The same pool_size / max_overflow settings apply; Cloud Run scales
horizontally so keep pool_size small (2–5) to avoid exhausting the
Cloud SQL connection limit across many instances.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str, *, echo: bool = False) -> None:
    """
    Initialise the async engine and session factory.
    Must be called before any DB access (i.e. in lifespan startup).
    """
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Set it in .env (local) or as a Cloud Run env var (prod)."
        )

    global _engine, _session_factory
    _engine = create_async_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,   # cheap liveness check on checkout
        pool_size=5,
        max_overflow=10,
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,  # don't lazy-load after commit
    )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("DB not initialized. Call init_db() in lifespan.")
    return _session_factory


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
