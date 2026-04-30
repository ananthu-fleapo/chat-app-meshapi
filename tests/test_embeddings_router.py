"""
Tests for POST /v1/embeddings.

Covers:
  happy path forwarding and usage logging
  default_model fallback
  rate limit and spend-cap enforcement
  free-model throttling
  upstream error normalization
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_key(*, default_model: str | None = "openai/text-embedding-3-small"):
    key = MagicMock()
    key.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    key.owner = "acme"
    key.rpm_limit = None
    key.rpd_limit = None
    key.spend_cap_usd = None
    key.default_model = default_model
    key.default_params = None
    return key


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    # Return a proper MagicMock result so scalar_one_or_none() → None (not a coroutine).
    # This ensures get_price_row() returns None and the capability check is skipped.
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    execute_result.scalars.return_value.all.return_value = []
    execute_result.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result)
    return session


@pytest.fixture
def client(mock_db_session):
    from app.main import create_app
    from app.auth.dependencies import get_authenticated_key
    from app.db.session import get_db_session
    from app.cache.redis_client import get_redis

    app = create_app()

    async def _override_db():
        yield mock_db_session

    async def _override_key():
        return _make_key()

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_authenticated_key] = _override_key
    app.dependency_overrides[get_redis] = lambda: None

    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def error_client(mock_db_session):
    from app.main import create_app
    from app.auth.dependencies import get_authenticated_key
    from app.db.session import get_db_session
    from app.cache.redis_client import get_redis

    app = create_app()

    async def _override_db():
        yield mock_db_session

    async def _override_key():
        return _make_key()

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_authenticated_key] = _override_key
    app.dependency_overrides[get_redis] = lambda: None

    return TestClient(app, raise_server_exceptions=False)


class TestEmbeddingsRouter:

    def test_happy_path_returns_upstream_body_and_logs_usage(self, client):
        body = {
            "object": "list",
            "data": [{"object": "embedding", "embedding": [0.1, 0.2], "index": 0}],
            "model": "openai/text-embedding-3-small",
            "usage": {"prompt_tokens": 8, "total_tokens": 8},
        }
        adapter = MagicMock()
        adapter.embeddings = AsyncMock(return_value=body)

        with patch("app.routers.embeddings.check_rate_limits", AsyncMock()), \
             patch("app.routers.embeddings.check_spend_cap", AsyncMock()), \
             patch("app.routers.embeddings.check_balance", AsyncMock(return_value=False)), \
             patch("app.routers.embeddings.resolve_routing", AsyncMock(return_value=("openrouter", None, None))), \
             patch("app.routers.embeddings.resolve_upstream_key", AsyncMock(return_value="upstream-key")), \
             patch("app.routers.embeddings.get_adapter", return_value=adapter), \
             patch("app.routers.embeddings.fire_usage_log") as mock_usage_log:
            resp = client.post(
                "/v1/embeddings",
                json={"model": "openai/text-embedding-3-small", "input": "hello"},
            )

        assert resp.status_code == 200
        assert resp.json() == body
        mock_usage_log.assert_called_once()
        assert mock_usage_log.call_args.kwargs["prompt_tokens"] == 8
        assert mock_usage_log.call_args.kwargs["completion_tokens"] == 0

    def test_omitted_model_uses_key_default_model(self, client):
        adapter = MagicMock()
        adapter.embeddings = AsyncMock(return_value={"object": "list", "data": [], "usage": {}})

        with patch("app.routers.embeddings.check_rate_limits", AsyncMock()), \
             patch("app.routers.embeddings.check_spend_cap", AsyncMock()), \
             patch("app.routers.embeddings.check_balance", AsyncMock(return_value=False)), \
             patch("app.routers.embeddings.resolve_routing", AsyncMock(return_value=("openrouter", None, None))), \
             patch("app.routers.embeddings.resolve_upstream_key", AsyncMock(return_value="upstream-key")), \
             patch("app.routers.embeddings.get_adapter", return_value=adapter), \
             patch("app.routers.embeddings.fire_usage_log"):
            resp = client.post("/v1/embeddings", json={"input": "hello"})

        assert resp.status_code == 200
        request_arg = adapter.embeddings.await_args.args[0]
        assert request_arg.model == "openai/text-embedding-3-small"

    def test_rate_limit_enforcement_returns_429(self, error_client):
        from app.exceptions import RateLimitError

        with patch(
            "app.routers.embeddings.check_rate_limits",
            AsyncMock(side_effect=RateLimitError("RPM limit exceeded.", retry_after=60)),
        ):
            resp = error_client.post(
                "/v1/embeddings",
                json={"model": "openai/text-embedding-3-small", "input": "hello"},
            )

        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "rate_limit_exceeded"

    def test_spend_cap_enforcement_returns_402(self, error_client, mock_db_session):
        from app.exceptions import PaymentRequiredError
        from app.auth.dependencies import get_authenticated_key

        key = _make_key()
        key.spend_cap_usd = 10.0

        def override_key():
            return key

        error_client.app.dependency_overrides[get_authenticated_key] = override_key

        with patch(
            "app.routers.embeddings.check_spend_cap",
            AsyncMock(side_effect=PaymentRequiredError()),
        ):
            resp = error_client.post(
                "/v1/embeddings",
                json={"model": "openai/text-embedding-3-small", "input": "hello"},
            )

        assert resp.status_code == 402
        assert resp.json()["error"]["code"] == "spend_limit_exceeded"

    def test_free_model_rate_limits_are_applied(self, client):
        adapter = MagicMock()
        adapter.embeddings = AsyncMock(return_value={"object": "list", "data": [], "usage": {}})

        with patch("app.routers.embeddings.check_rate_limits", AsyncMock()), \
             patch("app.routers.embeddings.check_spend_cap", AsyncMock()), \
             patch("app.routers.embeddings.check_balance", AsyncMock(return_value=True)), \
             patch("app.routers.embeddings.check_free_model_rate_limits", AsyncMock()) as mock_free_rl, \
             patch("app.routers.embeddings.resolve_routing", AsyncMock(return_value=("openrouter", None, None))), \
             patch("app.routers.embeddings.resolve_upstream_key", AsyncMock(return_value="upstream-key")), \
             patch("app.routers.embeddings.get_adapter", return_value=adapter), \
             patch("app.routers.embeddings.fire_usage_log"):
            resp = client.post(
                "/v1/embeddings",
                json={"model": "openai/text-embedding-3-small", "input": "hello"},
            )

        assert resp.status_code == 200
        mock_free_rl.assert_awaited_once()

    def test_upstream_error_is_normalized(self, error_client):
        from app.exceptions import UpstreamError

        adapter = MagicMock()
        adapter.embeddings = AsyncMock(side_effect=UpstreamError())

        with patch("app.routers.embeddings.check_rate_limits", AsyncMock()), \
             patch("app.routers.embeddings.check_spend_cap", AsyncMock()), \
             patch("app.routers.embeddings.check_balance", AsyncMock(return_value=False)), \
             patch("app.routers.embeddings.resolve_routing", AsyncMock(return_value=("openrouter", None, None))), \
             patch("app.routers.embeddings.resolve_upstream_key", AsyncMock(return_value="upstream-key")), \
             patch("app.routers.embeddings.get_adapter", return_value=adapter), \
             patch("app.routers.embeddings.fire_usage_log"):
            resp = error_client.post(
                "/v1/embeddings",
                json={"model": "openai/text-embedding-3-small", "input": "hello"},
            )

        assert resp.status_code == 500
        assert resp.json()["error"]["code"] == "upstream_error"
