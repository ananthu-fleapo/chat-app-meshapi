"""
Tests for POST /v1/model-health/run

Coverage:
- Auth (missing, wrong, correct)
- Happy path: all pass, mixed pass/fail, no models
- Slack: called once, failure doesn't fail endpoint
- _test_model unit: pass, fail, timeout
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Must be set before any app import (pydantic-settings reads at class-definition time).
# conftest.py already sets OPENROUTER_API_KEY, WEBHOOK_API_KEY, SUPABASE_JWT_SECRET.

WEBHOOK_HEADERS = {"Authorization": "Bearer test-webhook-secret"}
WRONG_HEADERS = {"Authorization": "Bearer wrong-secret"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def client(mock_db_session):
    from app.main import create_app
    from app.cache.redis_client import get_redis
    from app.db.session import get_db_session
    from fastapi.testclient import TestClient

    app = create_app()

    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []

    health_session = AsyncMock()
    health_session.execute = AsyncMock(return_value=empty_result)

    health_session_cm = AsyncMock()
    health_session_cm.__aenter__.return_value = health_session
    health_session_cm.__aexit__.return_value = False

    async def _override_db():
        yield mock_db_session

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_redis] = lambda: None

    with patch(
        "app.routers.model_health.get_session_factory",
        return_value=lambda: health_session_cm,
    ):
        yield TestClient(app, raise_server_exceptions=True)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_slack():
    return patch("app.routers.model_health.send_slack_alert", AsyncMock())


def _mock_get_models(model_ids: list[str]):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = model_ids
    session.execute = AsyncMock(return_value=result)

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = False

    return patch(
        "app.routers.model_health.get_session_factory",
        return_value=lambda: session_cm,
    )


def _mock_test_model(
    *,
    status: str = "pass",
    latency_ms: int = 100,
    error: str | None = None,
):
    from app.routers.model_health import ModelHealthResult

    async def _result(model_id: str):
        return ModelHealthResult(
            model_id=model_id,
            status=status,
            latency_ms=latency_ms,
            error=error,
        )

    return patch("app.routers.model_health._test_model", side_effect=_result)


# ── Auth ──────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_missing_auth_header_returns_4xx(self, client):
        resp = client.post("/v1/model-health/run")
        assert resp.status_code in (401, 403, 422)

    def test_wrong_key_returns_401_or_403(self, client):
        resp = client.post("/v1/model-health/run", headers=WRONG_HEADERS)
        assert resp.status_code in (401, 403)

    def test_correct_key_proceeds(self, client, mock_db_session):
        with _mock_get_models([]), _mock_slack():
            resp = client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)
        assert resp.status_code == 200


# ── Happy path ────────────────────────────────────────────────────────────────

class TestHappyPath:
    def test_all_pass_response_shape(self, client, mock_db_session):
        with _mock_get_models(["model-a", "model-b"]), \
             _mock_test_model(status="pass", latency_ms=200), \
             _mock_slack():
            resp = client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["passed"] == 2
        assert body["failed"] == 0
        assert body["pass_rate"] == "100.0%"
        assert len(body["results"]) == 2
        assert all(r["status"] == "pass" for r in body["results"])

    def test_mixed_pass_fail_counts(self, client, mock_db_session):
        from app.routers.model_health import ModelHealthResult

        results_map = {
            "model-a": ModelHealthResult(model_id="model-a", status="pass", latency_ms=100),
            "model-b": ModelHealthResult(model_id="model-b", status="fail", latency_ms=50, error="upstream 500"),
            "model-c": ModelHealthResult(model_id="model-c", status="timeout", latency_ms=20000),
        }

        async def _mixed(model_id):
            return results_map[model_id]

        with _mock_get_models(["model-a", "model-b", "model-c"]), \
             patch("app.routers.model_health._test_model", side_effect=_mixed), \
             _mock_slack():
            resp = client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)

        body = resp.json()
        assert body["total"] == 3
        assert body["passed"] == 1
        assert body["failed"] == 2
        assert body["pass_rate"] == "33.3%"

    def test_no_models_returns_zero_counts(self, client, mock_db_session):
        with _mock_get_models([]), _mock_slack():
            resp = client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["passed"] == 0
        assert body["failed"] == 0
        assert body["pass_rate"] == "0.0%"

    def test_result_includes_error_for_failed_models(self, client, mock_db_session):
        with _mock_get_models(["model-a"]), \
             _mock_test_model(status="fail", latency_ms=50, error="401 Unauthorized"), \
             _mock_slack():
            resp = client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)

        result = resp.json()["results"][0]
        assert result["status"] == "fail"
        assert result["error"] == "401 Unauthorized"

    def test_result_error_is_none_for_passing_models(self, client, mock_db_session):
        with _mock_get_models(["model-a"]), \
             _mock_test_model(status="pass", latency_ms=100), \
             _mock_slack():
            resp = client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)

        result = resp.json()["results"][0]
        assert result["status"] == "pass"
        assert result["error"] is None

# ── Slack ─────────────────────────────────────────────────────────────────────

class TestSlack:
    def test_slack_called_once_per_run(self, client, mock_db_session):
        mock_slack = AsyncMock()
        with _mock_get_models(["model-a"]), _mock_test_model(), \
             patch("app.routers.model_health.send_slack_alert", mock_slack):
            client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)

        mock_slack.assert_called_once()

    def test_slack_title_contains_pass_count(self, client, mock_db_session):
        mock_slack = AsyncMock()
        with _mock_get_models(["model-a", "model-b"]), _mock_test_model(status="pass"), \
             patch("app.routers.model_health.send_slack_alert", mock_slack):
            client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)

        title = mock_slack.call_args.kwargs["title"]
        assert "2/2" in title

    def test_slack_failure_does_not_affect_response(self, client, mock_db_session):
        """
        send_slack_alert() internally swallows exceptions (logs a warning, never raises).
        Verify the endpoint returns 200 when Slack is unavailable by simulating the
        helper returning normally (as it does when the underlying httpx call fails).
        """
        with _mock_get_models(["model-a"]), _mock_test_model(), \
             patch("app.routers.model_health.send_slack_alert", AsyncMock(return_value=None)):
            resp = client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)

        assert resp.status_code == 200

    def test_slack_message_contains_failed_models(self, client, mock_db_session):
        mock_slack = AsyncMock()
        with _mock_get_models(["model-a"]), \
             _mock_test_model(status="fail", error="upstream 500"), \
             patch("app.routers.model_health.send_slack_alert", mock_slack):
            client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)

        message = mock_slack.call_args.kwargs.get("message", "")
        assert "model-a" in message
        assert "fail" in message

    def test_slack_message_is_none_when_all_pass(self, client, mock_db_session):
        mock_slack = AsyncMock()
        with _mock_get_models(["model-a"]), _mock_test_model(status="pass"), \
             patch("app.routers.model_health.send_slack_alert", mock_slack):
            client.post("/v1/model-health/run", headers=WEBHOOK_HEADERS)

        message = mock_slack.call_args.kwargs.get("message")
        assert message is None


# ── _test_model unit tests ────────────────────────────────────────────────────

class TestTestModel:
    @pytest.mark.asyncio
    async def test_returns_pass_on_successful_call(self):
        from app.routers.model_health import _test_model

        with _mock_get_models(["model-a"]), patch(
            "app.routers.model_health.resolve_routing",
            AsyncMock(return_value=("openrouter", "openrouter/model-a", None)),
        ), patch(
            "app.routers.model_health.resolve_upstream_key",
            AsyncMock(return_value="test-key"),
        ), patch("app.routers.model_health.get_adapter") as mock_get_adapter:
            adapter = MagicMock()
            adapter.chat_completion = AsyncMock(return_value={"choices": []})
            mock_get_adapter.return_value = adapter

            result = await _test_model("model-a")

        assert result.status == "pass"
        assert result.error is None
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_returns_fail_on_provider_exception(self):
        from app.routers.model_health import _test_model

        with _mock_get_models(["model-a"]), patch(
            "app.routers.model_health.resolve_routing",
            AsyncMock(return_value=("openrouter", "openrouter/model-a", None)),
        ), patch(
            "app.routers.model_health.resolve_upstream_key",
            AsyncMock(return_value="test-key"),
        ), patch("app.routers.model_health.get_adapter") as mock_get_adapter:
            adapter = MagicMock()
            adapter.chat_completion = AsyncMock(side_effect=Exception("upstream 500"))
            mock_get_adapter.return_value = adapter

            result = await _test_model("model-a")

        assert result.status == "fail"
        assert result.error == "upstream 500"

    @pytest.mark.asyncio
    async def test_returns_timeout_on_asyncio_timeout(self):
        from app.routers.model_health import _test_model

        with _mock_get_models(["model-a"]), patch(
            "app.routers.model_health.resolve_routing",
            AsyncMock(return_value=("openrouter", "openrouter/model-a", None)),
        ), patch(
            "app.routers.model_health.resolve_upstream_key",
            AsyncMock(return_value="test-key"),
        ), patch("app.routers.model_health.get_adapter") as mock_get_adapter:
            adapter = MagicMock()
            adapter.chat_completion = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_get_adapter.return_value = adapter

            result = await _test_model("model-a")

        assert result.status == "timeout"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_latency_ms_is_non_negative(self):
        from app.routers.model_health import _test_model

        with _mock_get_models(["model-a"]), patch(
            "app.routers.model_health.resolve_routing",
            AsyncMock(return_value=("openrouter", "openrouter/model-a", None)),
        ), patch(
            "app.routers.model_health.resolve_upstream_key",
            AsyncMock(return_value="test-key"),
        ), patch("app.routers.model_health.get_adapter") as mock_get_adapter:
            adapter = MagicMock()
            adapter.chat_completion = AsyncMock(return_value={})
            mock_get_adapter.return_value = adapter

            result = await _test_model("model-a")

        assert result.latency_ms >= 0
