"""
Shared test fixtures.

Env vars are set before any app module is imported so pydantic-settings
reads them at class-definition time.
"""

import os

# ── Required env vars — set before app imports ────────────────────────────────
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("ENV", "dev")
os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("WEBHOOK_API_KEY", "test-webhook-secret")
# Empty JWT secret → dev bypass (any token string is accepted as owner)
os.environ.setdefault("SUPABASE_JWT_SECRET", "")

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_db():
    """Async SQLAlchemy session mock with sensible defaults."""
    session = AsyncMock()
    session.add = MagicMock()          # synchronous
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    # execute returns an AsyncMock; tests override .return_value as needed
    session.execute = AsyncMock()
    return session


def make_execute_result(rows=None, scalar=None):
    """
    Helper: build a mock result that mimics SQLAlchemy's async execute return.

    rows   — list of tuples returned by .all() / iterated
    scalar — single value returned by .scalar_one() / .scalar_one_or_none()
    """
    result = MagicMock()
    result.one_or_none.return_value = rows[0] if rows else None
    result.scalar_one.return_value = scalar
    result.scalar_one_or_none.return_value = scalar
    result.scalars.return_value.all.return_value = rows or []
    result.all.return_value = rows or []
    result.one.return_value = rows[0] if rows else None
    return result
