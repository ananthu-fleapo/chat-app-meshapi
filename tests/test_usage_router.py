"""
Tests for GET /v1/usage and GET /v1/usage/events

Covers:
  get_usage_summary  — no keys, with keys, date range filter
  get_usage_events   — no keys, pagination, status filter, model filter, date range
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_execute_result

OWNER = "test-owner"
KEY_ID_1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
KEY_ID_2 = uuid.UUID("00000000-0000-0000-0000-000000000002")
EVENT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
REQUEST_ID = "req_test_001"
MODEL = "openai/gpt-4o-mini"
CREATED_AT = datetime(2026, 3, 25, 10, 0, 0, tzinfo=timezone.utc)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_identity(owner: str = OWNER):
    from app.auth.control_plane import ControlPlaneIdentity
    return ControlPlaneIdentity(sub="test-sub-uuid", owner=owner)


def _make_usage_event(
    *,
    id: uuid.UUID = EVENT_ID,
    key_id: uuid.UUID = KEY_ID_1,
    status: str = "success",
    model: str = MODEL,
    prompt_tokens: int | None = 20,
    completion_tokens: int | None = 484,
    total_tokens: int | None = 504,
    cost_usd: Decimal | None = Decimal("0.00010000"),
    latency_ms: int | None = 850,
    error_code: str | None = None,
):
    event = MagicMock()
    event.id = id
    event.key_id = key_id
    event.request_id = REQUEST_ID
    event.model = model
    event.stream = False
    event.template_id = None
    event.prompt_tokens = prompt_tokens
    event.completion_tokens = completion_tokens
    event.total_tokens = total_tokens
    event.cost_usd = cost_usd
    event.cached_tokens = None
    event.latency_ms = latency_ms
    event.status = status
    event.error_code = error_code
    event.created_at = CREATED_AT
    return event


# ── get_usage_summary ─────────────────────────────────────────────────────────

class TestGetUsageSummary:

    async def test_no_keys_returns_zero_summary(self, mock_db):
        from app.routers.usage import get_usage_summary

        # No api keys for this owner — _owner_key_map returns {}
        mock_db.execute = AsyncMock(return_value=make_execute_result(rows=[], scalar=None))

        result = await get_usage_summary(
            since=None, until=None,
            identity=_make_identity(),
            db=mock_db,
        )

        assert result.total_requests == 0
        assert result.successful_requests == 0
        assert result.error_requests == 0
        assert result.by_model == []
        assert result.total_cost_usd is None

    async def test_with_keys_returns_aggregated_totals(self, mock_db):
        from app.routers.usage import get_usage_summary

        # First execute: key IDs lookup
        # Second execute: totals aggregate
        # Third execute: per-model breakdown
        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "prod-key"}), (KEY_ID_2, {"label": "dev-key"})])

        totals_row = MagicMock()
        totals_row.total = 10
        totals_row.success = 8
        totals_row.errors = 2
        totals_row.prompt_tokens = 500
        totals_row.completion_tokens = 2000
        totals_row.total_tokens = 2500
        totals_row.cost_usd = Decimal("0.05000000")
        totals_result = MagicMock()
        totals_result.one.return_value = totals_row

        breakdown_row = MagicMock()
        breakdown_row.model = MODEL
        breakdown_row.requests = 10
        breakdown_row.prompt_tokens = 500
        breakdown_row.completion_tokens = 2000
        breakdown_row.total_tokens = 2500
        breakdown_row.cost_usd = Decimal("0.05000000")
        breakdown_result = make_execute_result(rows=[breakdown_row])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, totals_result, breakdown_result]
        )

        result = await get_usage_summary(
            since=None, until=None,
            identity=_make_identity(),
            db=mock_db,
        )

        assert result.total_requests == 10
        assert result.successful_requests == 8
        assert result.error_requests == 2
        assert result.total_cost_usd == "0.05000000"
        assert len(result.by_model) == 1
        assert result.by_model[0].model == MODEL
        assert result.by_model[0].requests == 10

    async def test_date_range_is_forwarded(self, mock_db):
        """since/until params should not raise; queries are issued with them."""
        from app.routers.usage import get_usage_summary

        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "my-key"})])

        totals_row = MagicMock()
        totals_row.total = 0
        totals_row.success = 0
        totals_row.errors = 0
        totals_row.prompt_tokens = None
        totals_row.completion_tokens = None
        totals_row.total_tokens = None
        totals_row.cost_usd = None
        totals_result = MagicMock()
        totals_result.one.return_value = totals_row

        breakdown_result = make_execute_result(rows=[])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, totals_result, breakdown_result]
        )

        result = await get_usage_summary(
            since="2026-03-01",
            until="2026-03-31",
            identity=_make_identity(),
            db=mock_db,
        )

        assert result.total_requests == 0
        assert mock_db.execute.call_count == 3


# ── get_usage_events ──────────────────────────────────────────────────────────

class TestGetUsageEvents:

    async def test_no_keys_returns_empty_page(self, mock_db):
        from app.routers.usage import get_usage_events

        mock_db.execute = AsyncMock(return_value=make_execute_result(rows=[]))

        result = await get_usage_events(
            limit=50, offset=0,
            since=None, until=None, model=None, status=None,
            identity=_make_identity(),
            db=mock_db,
        )

        assert result.events == []
        assert result.total == 0
        assert result.limit == 50
        assert result.offset == 0

    async def test_returns_events_with_correct_shape(self, mock_db):
        from app.routers.usage import get_usage_events

        event = _make_usage_event()
        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "my-key"})])
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        events_result = make_execute_result(rows=[event])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, count_result, events_result]
        )

        result = await get_usage_events(
            limit=50, offset=0,
            since=None, until=None, model=None, status=None,
            identity=_make_identity(),
            db=mock_db,
        )

        assert result.total == 1
        assert len(result.events) == 1
        ev = result.events[0]
        assert ev.id == str(EVENT_ID)
        assert ev.key_id == str(KEY_ID_1)
        assert ev.key_label == "my-key"
        assert ev.model == MODEL
        assert ev.model_name == "gpt-4o-mini"
        assert ev.model_provider == "openai"
        assert ev.status == "success"
        assert ev.prompt_tokens == 20
        assert ev.completion_tokens == 484
        assert ev.cost_usd == "0.00010000"
        assert ev.latency_ms == 850
        assert ev.error_code is None
        # tps = 484 * 1000 / 850 ≈ 569.41
        assert ev.tokens_per_second == round(484 * 1000 / 850, 2)

    async def test_pagination_params_forwarded(self, mock_db):
        """limit and offset are reflected in the response."""
        from app.routers.usage import get_usage_events

        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "my-key"})])
        count_result = MagicMock()
        count_result.scalar_one.return_value = 200
        events_result = make_execute_result(rows=[])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, count_result, events_result]
        )

        result = await get_usage_events(
            limit=25, offset=100,
            since=None, until=None, model=None, status=None,
            identity=_make_identity(),
            db=mock_db,
        )

        assert result.limit == 25
        assert result.offset == 100
        assert result.total == 200

    async def test_status_filter_success(self, mock_db):
        """status='success' filter returns only successful events."""
        from app.routers.usage import get_usage_events

        event = _make_usage_event(status="success")
        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "my-key"})])
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        events_result = make_execute_result(rows=[event])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, count_result, events_result]
        )

        result = await get_usage_events(
            limit=50, offset=0,
            since=None, until=None, model=None, status="success",
            identity=_make_identity(),
            db=mock_db,
        )

        assert all(e.status == "success" for e in result.events)

    async def test_status_filter_error(self, mock_db):
        """status='error' filter returns only error events."""
        from app.routers.usage import get_usage_events

        event = _make_usage_event(status="error", error_code="RATE_LIMIT_EXCEEDED")
        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "my-key"})])
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        events_result = make_execute_result(rows=[event])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, count_result, events_result]
        )

        result = await get_usage_events(
            limit=50, offset=0,
            since=None, until=None, model=None, status="error",
            identity=_make_identity(),
            db=mock_db,
        )

        assert len(result.events) == 1
        assert result.events[0].status == "error"
        assert result.events[0].error_code == "RATE_LIMIT_EXCEEDED"

    async def test_model_filter(self, mock_db):
        """model filter restricts results to the given model string."""
        from app.routers.usage import get_usage_events

        specific_model = "anthropic/claude-3-5-haiku"
        event = _make_usage_event(model=specific_model)
        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "my-key"})])
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        events_result = make_execute_result(rows=[event])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, count_result, events_result]
        )

        result = await get_usage_events(
            limit=50, offset=0,
            since=None, until=None, model=specific_model, status=None,
            identity=_make_identity(),
            db=mock_db,
        )

        assert len(result.events) == 1
        assert result.events[0].model == specific_model

    async def test_null_cost_serialised_as_none(self, mock_db):
        """cost_usd=None on the ORM row → None in the response (not '0')."""
        from app.routers.usage import get_usage_events

        event = _make_usage_event(cost_usd=None)
        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "my-key"})])
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        events_result = make_execute_result(rows=[event])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, count_result, events_result]
        )

        result = await get_usage_events(
            limit=50, offset=0,
            since=None, until=None, model=None, status=None,
            identity=_make_identity(),
            db=mock_db,
        )

        assert result.events[0].cost_usd is None

    async def test_created_at_serialised_as_iso_string(self, mock_db):
        """created_at datetime is serialised to ISO 8601 string."""
        from app.routers.usage import get_usage_events

        event = _make_usage_event()
        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "my-key"})])
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        events_result = make_execute_result(rows=[event])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, count_result, events_result]
        )

        result = await get_usage_events(
            limit=50, offset=0,
            since=None, until=None, model=None, status=None,
            identity=_make_identity(),
            db=mock_db,
        )

        assert isinstance(result.events[0].created_at, str)
        # Must parse as ISO 8601 without raising
        datetime.fromisoformat(result.events[0].created_at)

    async def test_date_range_filter_does_not_raise(self, mock_db):
        """since/until params are accepted and queries complete without error."""
        from app.routers.usage import get_usage_events

        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "my-key"})])
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        events_result = make_execute_result(rows=[])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, count_result, events_result]
        )

        result = await get_usage_events(
            limit=50, offset=0,
            since="2026-03-01",
            until="2026-03-31",
            model=None, status=None,
            identity=_make_identity(),
            db=mock_db,
        )

        assert result.total == 0
        assert result.events == []

    async def test_key_label_none_when_label_not_set(self, mock_db):
        """key_label is None when the ApiKey has no label."""
        from app.routers.usage import get_usage_events

        event = _make_usage_event()
        keys_result = make_execute_result(rows=[(KEY_ID_1, {})])  # meta has no label
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        events_result = make_execute_result(rows=[event])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, count_result, events_result]
        )

        result = await get_usage_events(
            limit=50, offset=0,
            since=None, until=None, model=None, status=None,
            identity=_make_identity(),
            db=mock_db,
        )

        assert result.events[0].key_label is None


# ── _parse_dt ────────────────────────────────────────────────────────────────

class TestParseDt:

    def test_bare_date_as_until_includes_full_day(self):
        from app.routers.usage import _parse_dt
        dt = _parse_dt("2026-01-31", end_of_day=True)
        assert dt is not None
        assert dt.year == 2026 and dt.month == 1 and dt.day == 31
        assert dt.hour == 23 and dt.minute == 59 and dt.second == 59
        assert dt.microsecond == 999999

    def test_bare_date_as_since_keeps_midnight(self):
        from app.routers.usage import _parse_dt
        dt = _parse_dt("2026-01-01", end_of_day=False)
        assert dt is not None
        assert dt.hour == 0 and dt.minute == 0 and dt.second == 0

    def test_datetime_with_time_not_shifted(self):
        """If caller supplies an explicit time, end_of_day should not override it."""
        from app.routers.usage import _parse_dt
        dt = _parse_dt("2026-01-31T12:00:00", end_of_day=True)
        assert dt is not None
        assert dt.hour == 12 and dt.minute == 0

    def test_none_returns_none(self):
        from app.routers.usage import _parse_dt
        assert _parse_dt(None) is None

    def test_invalid_string_returns_none(self):
        from app.routers.usage import _parse_dt
        assert _parse_dt("not-a-date") is None


# ── _split_model ──────────────────────────────────────────────────────────────

class TestSplitModel:

    def test_standard_provider_slash_model(self):
        from app.routers.usage import _split_model
        name, provider = _split_model("openai/gpt-4o-mini")
        assert name == "gpt-4o-mini"
        assert provider == "openai"

    def test_no_slash_returns_model_and_none_provider(self):
        from app.routers.usage import _split_model
        name, provider = _split_model("gpt-4o")
        assert name == "gpt-4o"
        assert provider is None

    def test_variant_suffix_stays_in_model_name(self):
        from app.routers.usage import _split_model
        name, provider = _split_model("nvidia/llama-3.1-nemotron-70b-instruct:free")
        assert name == "llama-3.1-nemotron-70b-instruct:free"
        assert provider == "nvidia"


# ── _tokens_per_second ────────────────────────────────────────────────────────

class TestTokensPerSecond:

    def test_normal_values(self):
        from app.routers.usage import _tokens_per_second
        result = _tokens_per_second(completion_tokens=484, latency_ms=850)
        assert result == round(484 * 1000 / 850, 2)

    def test_none_completion_tokens_returns_none(self):
        from app.routers.usage import _tokens_per_second
        assert _tokens_per_second(completion_tokens=None, latency_ms=850) is None

    def test_none_latency_returns_none(self):
        from app.routers.usage import _tokens_per_second
        assert _tokens_per_second(completion_tokens=484, latency_ms=None) is None

    def test_zero_latency_returns_none(self):
        from app.routers.usage import _tokens_per_second
        assert _tokens_per_second(completion_tokens=484, latency_ms=0) is None

    def test_model_with_no_provider_serialised_correctly(self, mock_db):
        """model with no '/' → model_name equals model, model_provider is None."""
        ...

    async def test_event_with_no_provider_model(self, mock_db):
        from app.routers.usage import get_usage_events

        event = _make_usage_event(model="gpt-4o")
        keys_result = make_execute_result(rows=[(KEY_ID_1, {"label": "my-key"})])
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        events_result = make_execute_result(rows=[event])

        mock_db.execute = AsyncMock(
            side_effect=[keys_result, count_result, events_result]
        )

        result = await get_usage_events(
            limit=50, offset=0,
            since=None, until=None, model=None, status=None,
            identity=_make_identity(),
            db=mock_db,
        )

        ev = result.events[0]
        assert ev.model_name == "gpt-4o"
        assert ev.model_provider is None
