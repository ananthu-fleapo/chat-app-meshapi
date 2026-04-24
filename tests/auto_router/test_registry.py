"""
Unit tests for app/auto_router/registry.py

Covers:
  get_enabled_models — warm cache hit, cold path (filter + populate cache), _supports filtering
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_model_out(
    id_: str,
    *,
    supports_completions_api: bool = True,
    supports_responses_api: bool = False,
    supports_embeddings_api: bool = False,
    description: str | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = id_
    m.name = f"{id_} name"
    m.description = description
    m.supports_completions_api = supports_completions_api
    m.supports_responses_api = supports_responses_api
    m.supports_embeddings_api = supports_embeddings_api
    return m


class TestGetEnabledModelsWarmCache:

    async def test_warm_cache_hit_skips_get_models(self):
        from app.auto_router.registry import CandidateModel, get_enabled_models

        cached_data = json.dumps([{"model_id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "description": "Fast"}])
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached_data)

        with (
            patch("app.auto_router.registry.get_redis", return_value=mock_redis),
            patch("app.routers.models._get_models") as mock_get_models,
        ):
            result = await get_enabled_models("completions")

        assert len(result) == 1
        assert result[0].model_id == "openai/gpt-4o-mini"
        mock_get_models.assert_not_called()

    async def test_cache_miss_populates_cache(self):
        from app.auto_router.registry import get_enabled_models

        mock_models = [
            _make_model_out("openai/gpt-4o-mini", supports_completions_api=True),
        ]
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        with (
            patch("app.auto_router.registry.get_redis", return_value=mock_redis),
            patch("app.routers.models._get_models", AsyncMock(return_value=mock_models)),
        ):
            result = await get_enabled_models("completions")

        assert len(result) == 1
        assert result[0].model_id == "openai/gpt-4o-mini"
        mock_redis.setex.assert_called_once()

    async def test_redis_unavailable_falls_through_to_models(self):
        from app.auto_router.registry import get_enabled_models

        mock_models = [_make_model_out("openai/gpt-4o-mini")]

        with (
            patch("app.auto_router.registry.get_redis", return_value=None),
            patch("app.routers.models._get_models", AsyncMock(return_value=mock_models)),
        ):
            result = await get_enabled_models("completions")

        assert len(result) == 1


class TestGetEnabledModelsFiltering:

    async def test_filters_by_completions_api(self):
        from app.auto_router.registry import get_enabled_models

        models = [
            _make_model_out("chat-model", supports_completions_api=True, supports_embeddings_api=False),
            _make_model_out("embed-model", supports_completions_api=False, supports_embeddings_api=True),
        ]

        with (
            patch("app.auto_router.registry.get_redis", return_value=None),
            patch("app.routers.models._get_models", AsyncMock(return_value=models)),
        ):
            result = await get_enabled_models("completions")

        assert len(result) == 1
        assert result[0].model_id == "chat-model"

    async def test_filters_by_responses_api(self):
        from app.auto_router.registry import get_enabled_models

        models = [
            _make_model_out("reasoning-model", supports_completions_api=True, supports_responses_api=True),
            _make_model_out("chat-model", supports_completions_api=True, supports_responses_api=False),
        ]

        with (
            patch("app.auto_router.registry.get_redis", return_value=None),
            patch("app.routers.models._get_models", AsyncMock(return_value=models)),
        ):
            result = await get_enabled_models("responses")

        assert len(result) == 1
        assert result[0].model_id == "reasoning-model"

    async def test_filters_by_embeddings_api(self):
        from app.auto_router.registry import get_enabled_models

        models = [
            _make_model_out("embed-model", supports_completions_api=False, supports_embeddings_api=True),
            _make_model_out("chat-model", supports_completions_api=True, supports_embeddings_api=False),
        ]

        with (
            patch("app.auto_router.registry.get_redis", return_value=None),
            patch("app.routers.models._get_models", AsyncMock(return_value=models)),
        ):
            result = await get_enabled_models("embeddings")

        assert len(result) == 1
        assert result[0].model_id == "embed-model"

    async def test_description_truncated_to_80_chars(self):
        from app.auto_router.registry import get_enabled_models

        long_desc = "A" * 200
        models = [_make_model_out("m", description=long_desc)]

        with (
            patch("app.auto_router.registry.get_redis", return_value=None),
            patch("app.routers.models._get_models", AsyncMock(return_value=models)),
        ):
            result = await get_enabled_models("completions")

        assert len(result[0].description) == 80

    async def test_none_description_becomes_empty_string(self):
        from app.auto_router.registry import get_enabled_models

        models = [_make_model_out("m", description=None)]

        with (
            patch("app.auto_router.registry.get_redis", return_value=None),
            patch("app.routers.models._get_models", AsyncMock(return_value=models)),
        ):
            result = await get_enabled_models("completions")

        assert result[0].description == ""

    async def test_returns_empty_list_when_no_models_match(self):
        from app.auto_router.registry import get_enabled_models

        models = [_make_model_out("embed-model", supports_completions_api=False, supports_embeddings_api=True)]

        with (
            patch("app.auto_router.registry.get_redis", return_value=None),
            patch("app.routers.models._get_models", AsyncMock(return_value=models)),
        ):
            result = await get_enabled_models("completions")

        assert result == []
