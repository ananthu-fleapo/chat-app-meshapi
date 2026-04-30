"""
Test router — POST /test/responses

Simple passthrough for local development. No auth, no rate limiting.
Uses the system API key for the given provider.

On pass, upserts the model into `models` + `model_prices` + `model_pricing`
with supports_responses_api=True.

Only registered when ENV=dev. Never ship this to production.
"""

import asyncio
from datetime import date as _date
from decimal import Decimal
from typing import cast

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.control_plane import ControlPlaneIdentity, get_admin_user
from app.config import settings
from app.db.models import Model, ModelPrice, ModelPricing
from app.db.session import get_db_session
from app.providers.registry import get_adapter
from app.schemas.responses import BuiltinTool, ResponsesRequest, Tool

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

    # ── V2 identity / modality ────────────────────────────────────────────────
    pricing_unit: str = "per_1k_tokens"
    """per_1k_tokens | per_1m_tokens | per_image | per_second | per_minute
    | per_request | per_session | per_call"""
    currency: str = "USD"
    modality: list[str] = ["text"]
    input_modalities: list[str] | None = None
    output_modalities: list[str] | None = None

    # ── V2 capability flags ───────────────────────────────────────────────────
    supports_thinking: bool = False
    supports_completions_api: bool = False
    supports_responses_api: bool = True
    supports_embeddings: bool = False
    supports_batching: bool = False
    supports_tools: bool = False
    supports_structured_output: bool = False
    supports_system_prompt: bool = True

    # ── V2 context & base costs ───────────────────────────────────────────────
    context_window: int | None = None
    request_cost: float | None = None

    # ── V2 long-context tiers ─────────────────────────────────────────────────
    standard_context_threshold: int | None = None
    long_context_input_cost: float | None = None
    long_context_output_cost: float | None = None

    # ── V2 prompt-caching costs (standard context) ────────────────────────────
    cache_read_input_cost: float | None = None
    cache_write_input_cost: float | None = None

    # ── V2 prompt-caching costs (long context) ────────────────────────────────
    long_context_cache_read_input_cost: float | None = None
    long_context_cache_write_input_cost: float | None = None

    # ── V2 batch pricing ──────────────────────────────────────────────────────
    batch_input_cost: float | None = None
    batch_output_cost: float | None = None

    # ── V2 fine-tuning costs ──────────────────────────────────────────────────
    training_cost: float | None = None
    fine_tuned_input_cost: float | None = None
    fine_tuned_output_cost: float | None = None

    # ── V2 modality-specific costs ────────────────────────────────────────────
    image_input_cost: float | None = None
    image_output_cost: float | None = None
    image_output_size: str | None = None
    audio_input_cost: float | None = None
    audio_output_cost: float | None = None
    transcription_cost: float | None = None

    # ── V2 lifecycle / metadata ───────────────────────────────────────────────
    priority: int | None = None
    notes: str | None = None
    source_url: str | None = None


class TestResponsesRequest(BaseModel):
    models: list[ModelEntry]
    input: str | list
    provider: str = "qwen"
    max_output_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    reasoning: dict | None = None  # {"effort": "minimal|low|medium|high"}
    tools: list[dict] | None = None
    """
    Built-in or function tools forwarded to the Responses API, e.g.
    [{"type": "image_generation"}] for image models.
    """


class ModelResult(BaseModel):
    model_id: str
    status: str  # "pass" | "fail"


async def _upsert_model_price(
    entry: ModelEntry,
    provider: str,
    db: AsyncSession,
) -> None:
    """
    Ensure models + model_prices (v1) + model_pricing (v2) rows exist for a
    passing model.

    - models: INSERT if not exists.
    - model_prices: INSERT or UPDATE for (model_id, provider).
      supports_responses_api is always set to True.
    - model_pricing: INSERT or UPDATE for (model_id, provider).
      supports_responses_api is always set to True.
    """
    model_id = entry.model_id
    brand = model_id.split("/")[0] if "/" in model_id else model_id
    prompt = Decimal(entry.prompt_usd_per_1k)
    completion = Decimal(entry.completion_usd_per_1k)
    responses_mid = entry.responses_provider_model_id

    # 1. Ensure models row exists
    model_exists = await db.execute(select(Model.model_id).where(Model.model_id == model_id))
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

    # 2. model_prices (v1) — INSERT or UPDATE
    existing_price = await db.execute(
        select(ModelPrice).where(
            ModelPrice.model_id == model_id,
            ModelPrice.provider == provider,
        )
    )
    price_row = existing_price.scalar_one_or_none()

    if price_row is None:
        await db.execute(
            pg_insert(ModelPrice).values(
                model_id=model_id,
                provider=provider,
                prompt_usd_per_1k=prompt,
                completion_usd_per_1k=completion,
                supports_responses_api=True,
                supports_completions_api=entry.supports_completions_api,
                responses_provider_model_id=responses_mid,
                is_default=True,
                is_free=False,
            )
        )
        logger.info("test_model_price_inserted", model_id=model_id, provider=provider)
    else:
        price_row.supports_responses_api = True
        if responses_mid != price_row.provider_model_id:
            price_row.responses_provider_model_id = responses_mid
        logger.info("test_model_price_updated", model_id=model_id, provider=provider)

    # 3. model_pricing (v2) — INSERT or UPDATE
    existing_v2 = await db.execute(
        select(ModelPricing).where(
            ModelPricing.model_id == model_id,
            ModelPricing.provider == provider,
            ModelPricing.is_active.is_(True),
        )
    )
    v2_row = existing_v2.scalar_one_or_none()

    if v2_row is None:
        v2_row = ModelPricing(
            model_id=model_id,
            provider=provider,
            provider_model_id=responses_mid,
            model_name=model_id,
            modality=entry.modality,
            input_modalities=entry.input_modalities,
            output_modalities=entry.output_modalities,
            supports_tools=entry.supports_tools,
            supports_structured_output=entry.supports_structured_output,
            supports_system_prompt=entry.supports_system_prompt,
            supports_thinking=entry.supports_thinking,
            supports_batching=entry.supports_batching,
            supports_completions_api=entry.supports_completions_api,
            supports_responses_api=True,
            supports_embeddings=entry.supports_embeddings,
            pricing_unit=entry.pricing_unit,
            currency=entry.currency,
            input_cost=prompt,
            output_cost=completion,
            request_cost=entry.request_cost,
            context_window=entry.context_window,
            standard_context_threshold=entry.standard_context_threshold,
            long_context_input_cost=entry.long_context_input_cost,
            long_context_output_cost=entry.long_context_output_cost,
            cache_read_input_cost=entry.cache_read_input_cost,
            cache_write_input_cost=entry.cache_write_input_cost,
            long_context_cache_read_input_cost=entry.long_context_cache_read_input_cost,
            long_context_cache_write_input_cost=entry.long_context_cache_write_input_cost,
            batch_input_cost=entry.batch_input_cost,
            batch_output_cost=entry.batch_output_cost,
            training_cost=entry.training_cost,
            fine_tuned_input_cost=entry.fine_tuned_input_cost,
            fine_tuned_output_cost=entry.fine_tuned_output_cost,
            image_input_cost=entry.image_input_cost,
            image_output_cost=entry.image_output_cost,
            image_output_size=entry.image_output_size,
            audio_input_cost=entry.audio_input_cost,
            audio_output_cost=entry.audio_output_cost,
            transcription_cost=entry.transcription_cost,
            is_default=True,
            is_active=True,
            is_free=False,
            priority=entry.priority,
            effective_date=_date.today(),
            notes=entry.notes,
            source_url=entry.source_url,
        )
        db.add(v2_row)
        logger.info("test_model_pricing_v2_inserted", model_id=model_id, provider=provider)
    else:
        v2_row.supports_responses_api = True
        v2_row.input_cost = prompt
        v2_row.output_cost = completion
        logger.info("test_model_pricing_v2_updated", model_id=model_id, provider=provider)


@router.post("/responses", response_model=list[ModelResult])
async def test_responses(
    body: TestResponsesRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: ControlPlaneIdentity = Depends(get_admin_user),  # noqa: B008
):
    """
    Test multiple models and return pass/fail for each.

    All models are probed in parallel against the given provider using
    responses_provider_model_id. On pass the model is upserted into
    `models`, `model_prices`, and `model_pricing` with supports_responses_api=True.
    Only available in dev (ENV=dev).

    **Image model example** (gpt-image-2 via Responses API):

        curl -X POST http://localhost:8000/test/responses \\
          -H "Content-Type: application/json" \\
          -d '{
            "models": [{
              "model_id": "openai/gpt-image-2",
              "responses_provider_model_id": "gpt-image-2",
              "prompt_usd_per_1k": "0",
              "completion_usd_per_1k": "0",
              "pricing_unit": "per_image",
              "modality": ["image"],
              "image_output_cost": 0.04,
              "supports_completions_api": false,
              "supports_responses_api": true
            }],
            "input": "Generate a small red circle",
            "provider": "openai",
            "tools": [{"type": "image_generation"}]
          }'

    **Text model example**:

        curl -X POST http://localhost:8000/test/responses \\
          -H "Content-Type: application/json" \\
          -d '{
            "models": [{
              "model_id": "qwen/qwen3-max",
              "responses_provider_model_id": "qwen3-max",
              "prompt_usd_per_1k": "0.005",
              "completion_usd_per_1k": "0.005"
            }],
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
            tools=cast(list[Tool | BuiltinTool] | None, body.tools),
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
    for entry, result in zip(body.models, results, strict=True):
        if result.status == "pass":
            await _upsert_model_price(entry, body.provider, db)

    return list(results)
