"""
Alembic async migration environment.

Uses asyncpg (SQLAlchemy async) so migration runs use the same driver
as the application — no separate sync connection needed.

Running migrations
------------------
Local:
    alembic upgrade head

GCP (Cloud Run Job — same image, different CMD):
    CMD ["alembic", "upgrade", "head"]

The DATABASE_URL env var is read from Settings, so the same command
works for local dev (TCP) and Cloud Run (Cloud SQL Unix socket).
"""

import asyncio
import logging
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── App imports ───────────────────────────────────────────────────────────────
# Import settings + models so Alembic can diff against the ORM metadata.
from app.config import settings          # noqa: E402
from app.db.models import Base           # noqa: E402

# Override the URL from alembic.ini with the env-var value.
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata

# ── Offline mode (emit SQL to stdout, no live DB) ─────────────────────────────

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connect to live DB) ─────────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Include schemas so Alembic detects index changes too.
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # one-shot: no pool needed for migrations
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
