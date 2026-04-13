"""
Test router — POST /test/responses

Simple passthrough for local development. No auth, no rate limiting.
Uses the system API key for the given provider.

On pass, upserts the model into `models` + `model_prices` with
supports_responses_api=True.

Only registered when ENV=dev. Never ship this to production.
"""

import asyncio
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.control_plane import ControlPlaneIdentity, get_admin_user
from app.config import settings
from app.db.models import Model, ModelPrice
from app.db.session import get_db_session
from app.providers.registry import get_adapter
from app.schemas.responses import ResponsesRequest

router = APIRouter(prefix="/test", tags=["test"])
logger = structlog.get_logger()


_PROVIDER_KEYS: dict[str, str] = {
    "openrouter": "openrouter_api_key",
    "openai": "openai_api_key",
    "qwen": "qwen_api_key",
    "bedrock": "bedrock_api_key",
}


class ModelEntry(BaseModel):
    model_id: str
    responses_provider_model_id: str
    prompt_usd_per_1k: str
    completion_usd_per_1k: str
    context_length: int | None = None
    description: str | None = None


class TestResponsesRequest(BaseModel):
    models: list[ModelEntry]
    input: str | list
    provider: str = "qwen"
    max_output_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    reasoning: dict | None = None  # {"effort": "minimal|low|medium|high"}


class ModelResult(BaseModel):
    model_id: str
    status: str          # "pass" | "fail"


async def _upsert_model_price(
    entry: ModelEntry,
    provider: str,
    db: AsyncSession,
) -> None:
    """
    Ensure models + model_prices rows exist for a passing model.

    - models: INSERT if not exists.
    - model_prices: INSERT or UPDATE for (model_id, provider).
      supports_responses_api is always set to True.
      responses_provider_model_id is saved when it differs from
      the existing provider_model_id (so the responses path uses
      the correct provider-native ID).
    """
    model_id = entry.model_id
    brand = model_id.split("/")[0] if "/" in model_id else model_id

    # 1. Ensure models row exists
    model_exists = await db.execute(
        select(Model.model_id).where(Model.model_id == model_id)
    )
    if model_exists.scalar_one_or_none() is None:
        await db.execute(
            pg_insert(Model)
            .values(
                model_id=model_id,
                name=model_id,
                brand=brand,
                is_enabled=True,
                context_length=entry.context_length,
                description=entry.description,
            )
            .on_conflict_do_nothing(index_elements=["model_id"])
        )
        logger.info("test_model_inserted", model_id=model_id)

    # 2. Check existing model_prices row
    existing_price = await db.execute(
        select(ModelPrice).where(
            ModelPrice.model_id == model_id,
            ModelPrice.provider == provider,
        )
    )
    price_row = existing_price.scalar_one_or_none()

    responses_mid = entry.responses_provider_model_id

    if price_row is None:
        # New row — save responses_provider_model_id directly
        await db.execute(
            pg_insert(ModelPrice).values(
                model_id=model_id,
                provider=provider,
                prompt_usd_per_1k=Decimal(entry.prompt_usd_per_1k),
                completion_usd_per_1k=Decimal(entry.completion_usd_per_1k),
                supports_responses_api=True,
                supports_completions_api=False,
                responses_provider_model_id=responses_mid,
                is_default=True,
                is_free=False,
            )
        )
        logger.info("test_model_price_inserted", model_id=model_id, provider=provider)
    else:
        # Existing row — enable responses API and set override ID if needed
        price_row.supports_responses_api = True
        if responses_mid != price_row.provider_model_id:
            price_row.responses_provider_model_id = responses_mid
        logger.info("test_model_price_updated", model_id=model_id, provider=provider)


@router.post("/responses", response_model=list[ModelResult])
async def test_responses(
    body: TestResponsesRequest,
    db: AsyncSession = Depends(get_db_session),
    _: ControlPlaneIdentity = Depends(get_admin_user),
):
    """
    Test multiple models and return pass/fail for each.

    All models are probed in parallel against the given provider using
    responses_provider_model_id. On pass the model is upserted into
    `models` and `model_prices` with supports_responses_api=True.
    Only available in dev (ENV=dev).

    Example:
        curl -X POST http://localhost:8000/test/responses \\
          -H "Content-Type: application/json" \\
          -d '{
            "models": [{"model_id": "qwen/qwen3-max", "responses_provider_model_id": "qwen3-max", "prompt_usd_per_1k": "0.005", "completion_usd_per_1k": "0.005"}],
            "input": "Say hi",
            "provider": "qwen"
          }'
    """
    adapter = get_adapter(body.provider)
    key_attr = _PROVIDER_KEYS.get(body.provider)
    api_key = getattr(settings, key_attr, None) if key_attr else None

    async def probe(entry: ModelEntry) -> ModelResult:
        req = ResponsesRequest(
            model=entry.responses_provider_model_id,
            input=body.input,
            stream=False,
            max_output_tokens=body.max_output_tokens,
            temperature=body.temperature,
            reasoning=body.reasoning,
        )
        try:
            await adapter.responses_create(req, api_key=api_key)
            logger.info("test_model_pass", model_id=entry.model_id)
            return ModelResult(model_id=entry.model_id, status="pass")
        except Exception as exc:
            logger.warning("test_model_fail", model_id=entry.model_id, error=str(exc))
            return ModelResult(model_id=entry.model_id, status="fail")

    results = await asyncio.gather(*[probe(e) for e in body.models])

    # Upsert passing models into the DB
    for entry, result in zip(body.models, results):
        if result.status == "pass":
            await _upsert_model_price(entry, body.provider, db)

    return list(results)
