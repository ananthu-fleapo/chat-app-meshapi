"""
Test router — POST /test/completions

Streams SSE results for each model tested against the chat completions API.
No auth beyond admin JWT. Uses server-side credentials for the given provider.

On pass, upserts the model into `models` + `model_prices` + `model_pricing`
with is_enabled=true and is_default=true (unless is_dry_run=True).

Only registered when ENV=dev. Never ship this to production.
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Literal

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.auth.control_plane import ControlPlaneIdentity, get_admin_user
from app.db.models import Model, ModelPrice, ModelPricing

router = APIRouter(prefix="/test", tags=["test"])
logger = structlog.get_logger()


class TestModelItem(BaseModel):
    model_id: str
    """Canonical RouterSVC model ID, e.g. 'anthropic/claude-3-haiku'."""
    provider_model_id: str | None = None
    """
    Exact upstream model ID the provider expects, e.g.
    'us.anthropic.claude-3-haiku-20240307-v1:0' for Bedrock.
    If omitted, the adapter falls back to its internal _MODEL_MAP translation.
    Stored in model_prices.provider_model_id on success.
    """
    input_token_cost_per_1k: float | None = None
    output_token_cost_per_1k: float | None = None

    # ── V2 identity / modality ────────────────────────────────────────────────
    pricing_unit: str = "per_1k_tokens"
    """per_1k_tokens | per_1m_tokens | per_image | per_second | per_minute
    | per_request | per_session | per_call"""
    currency: str = "USD"
    modality: list[str] = ["text"]
    """Primary modality array, e.g. ["text", "image"]"""
    input_modalities: list[str] | None = None
    output_modalities: list[str] | None = None

    # ── V2 capability flags ───────────────────────────────────────────────────
    supports_thinking: bool = False
    supports_completions_api: bool = True
    supports_responses_api: bool = False
    supports_embeddings: bool = False
    supports_batching: bool = False
    supports_tools: bool = False
    supports_structured_output: bool = False
    supports_system_prompt: bool = True

    # ── V2 context & base costs ───────────────────────────────────────────────
    context_window: int | None = None
    request_cost: float | None = None
    """Flat cost per request (USD), if applicable."""

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
    """e.g. '1024x1024'"""
    audio_input_cost: float | None = None
    audio_output_cost: float | None = None
    transcription_cost: float | None = None

    # ── V2 lifecycle / metadata ───────────────────────────────────────────────
    priority: int | None = None
    notes: str | None = None
    source_url: str | None = None

    # ── Test behaviour ────────────────────────────────────────────────────────
    test_modality: Literal["completions", "image"] = "completions"
    """
    How to probe this model during the test.
    'completions' (default) — sends a chat completion request.
    'image'                  — calls the image generation endpoint instead;
                               use for models like gpt-image-1 or Imagen.
    """
    skip_test: bool = False
    """
    When True, skip the live probe and treat the model as passed immediately.
    Use for models that can't be called during registration (e.g. image models
    on providers without image generation support, or known-good models).
    """


class TestModelsRequest(BaseModel):
    is_dry_run: bool = True

    provider: str
    """
    Provider slug to test against: openrouter | vertex | bedrock | openai | qwen.
    Credentials are read from server config — no keys in the request body.
    """
    models: list[TestModelItem]
    """List of models to test."""
    prompt: str = "Reply with just the word OK and nothing else."
    image_prompt: str = "A red circle on a white background."
    """Prompt used when a model's test_modality is 'image'."""
    timeout: float = 30.0


def _derive_model_name(model_id: str) -> str:
    """Derive a human-readable display name from a canonical model ID."""
    slug = model_id.split("/", 1)[-1]
    return slug.replace("-", " ").replace("_", " ").replace(".", " ").title()


async def _test_models_stream(body: TestModelsRequest) -> AsyncGenerator[bytes, None]:
    """
    Async generator that tests each model against the provider, writes results
    to the DB, and yields SSE events.

    Per-model DB logic
    ------------------
    models row         — INSERT if not exists (is_enabled=false); on pass → SET is_enabled=true
    model_prices row   — INSERT if not exists (price=0, is_default=false); on pass →
                         clear other defaults, then SET is_default=true
    model_pricing row  — INSERT if not exists (all v2 fields); on pass →
                         clear other defaults, then SET is_default=true
    All inserts use ON CONFLICT DO NOTHING — existing rows are never overwritten.
    """
    from datetime import date as _date

    from app.db.engine import get_session_factory
    from app.providers.image_handler import _SUPPORTED_PROVIDERS as _IMAGE_PROVIDERS
    from app.providers.image_handler import generate_images
    from app.providers.registry import get_adapter
    from app.schemas.chat import ChatCompletionRequest, ImageOptions, Message

    # Validate provider has a registered adapter before streaming anything
    try:
        adapter = get_adapter(body.provider)
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n".encode()
        return

    session_factory = get_session_factory()
    passed = failed = 0

    for item in body.models:
        model_id = item.model_id
        provider_model_id = item.provider_model_id
        prompt_usd_per_1k = item.input_token_cost_per_1k
        completion_usd_per_1k = item.output_token_cost_per_1k
        t0 = time.monotonic()
        status = "fail"
        error: str | None = None

        # ── Test the model ─────────────────────────────────────────────────
        if item.skip_test:
            status = "pass"
        elif item.test_modality == "image":
            if body.provider not in _IMAGE_PROVIDERS:
                status = "fail"
                error = f"Provider '{body.provider}' does not support image generation"
            else:
                try:
                    items = await asyncio.wait_for(
                        generate_images(
                            body.image_prompt,
                            provider=body.provider,
                            provider_model_id=provider_model_id or model_id,
                            opts=ImageOptions(n=1),
                            api_key=None,
                        ),
                        timeout=body.timeout,
                    )
                    if items and (items[0].url or items[0].b64_json):
                        status = "pass"
                    else:
                        status = "fail"
                        error = "No image returned"
                except TimeoutError:
                    status = "timeout"
                    error = f"Timed out after {body.timeout:.0f}s"
                except Exception as exc:  # noqa: BLE001
                    status = "fail"
                    error = str(exc)[:200]
        else:
            req = ChatCompletionRequest(
                model=model_id,
                messages=[Message(role="user", content=body.prompt)],
                max_tokens=32,
                stream=False,
            )
            try:
                resp = await asyncio.wait_for(
                    adapter.chat_completion(
                        req,
                        api_key=None,
                        owner=None,
                        provider_model_id=provider_model_id,
                    ),
                    timeout=body.timeout,
                )
                # Verify the model responded — check content OR finish_reason
                # (reasoning models like gpt-5 may return null content)
                choice = (resp.get("choices") or [{}])[0]
                text = (choice.get("message", {}).get("content") or "").strip()
                finish_reason = choice.get("finish_reason") or ""
                if text or finish_reason:
                    status = "pass"
                else:
                    status = "fail"
                    error = "Empty response content"
            except TimeoutError:
                status = "timeout"
                error = f"Timed out after {body.timeout:.0f}s"
            except Exception as exc:  # noqa: BLE001
                status = "fail"
                error = str(exc)[:200]

        latency_ms = int((time.monotonic() - t0) * 1000)
        test_passed = status == "pass"
        is_default = False

        if test_passed:
            passed += 1
        else:
            failed += 1

        # ── DB writes (on pass, or skip_test bypasses is_dry_run) ────────────
        if test_passed and (not body.is_dry_run or item.skip_test):
            name = _derive_model_name(model_id)
            # provider_model_id is NOT NULL in both pricing tables — fall back to model_id
            effective_provider_model_id = provider_model_id or model_id
            # prompt/completion costs are NOT NULL in model_prices — image models legitimately
            # have zero token costs, so coerce None → 0.0 rather than letting the insert fail
            effective_prompt_cost = prompt_usd_per_1k if prompt_usd_per_1k is not None else 0.0
            effective_completion_cost = (
                completion_usd_per_1k if completion_usd_per_1k is not None else 0.0
            )
            try:
                async with session_factory() as db:
                    # 1. Insert model row if it doesn't exist (disabled by default)
                    await db.execute(
                        pg_insert(Model)
                        .values(
                            model_id=model_id,
                            name=name,
                            context_length=None,
                            brand=model_id.split("/")[0],
                            description=None,
                            is_enabled=False,
                        )
                        .on_conflict_do_nothing(index_elements=["model_id"])
                    )

                    # 2. Insert model_prices (v1) row if (model_id, provider) not present
                    await db.execute(
                        pg_insert(ModelPrice)
                        .values(
                            model_id=model_id,
                            provider=body.provider,
                            provider_model_id=effective_provider_model_id,
                            is_default=False,
                            prompt_usd_per_1k=effective_prompt_cost,
                            completion_usd_per_1k=effective_completion_cost,
                            is_free=False,
                        )
                        .on_conflict_do_nothing(index_elements=["model_id", "provider"])
                    )

                    # 2b. Insert model_pricing (v2) row if (model_id, provider) not present
                    await db.execute(
                        pg_insert(ModelPricing)
                        .values(
                            # Identity
                            model_id=model_id,
                            provider=body.provider,
                            provider_model_id=effective_provider_model_id,
                            model_name=name,
                            # Modality & capabilities
                            modality=item.modality,
                            input_modalities=item.input_modalities,
                            output_modalities=item.output_modalities,
                            supports_tools=item.supports_tools,
                            supports_structured_output=item.supports_structured_output,
                            supports_system_prompt=item.supports_system_prompt,
                            supports_thinking=item.supports_thinking,
                            supports_batching=item.supports_batching,
                            supports_completions_api=item.supports_completions_api,
                            supports_responses_api=item.supports_responses_api,
                            supports_embeddings=item.supports_embeddings,
                            # Pricing unit & base costs
                            pricing_unit=item.pricing_unit,
                            currency=item.currency,
                            input_cost=prompt_usd_per_1k,
                            output_cost=completion_usd_per_1k,
                            request_cost=item.request_cost,
                            # Context window & long-context tiers
                            context_window=item.context_window,
                            standard_context_threshold=item.standard_context_threshold,
                            long_context_input_cost=item.long_context_input_cost,
                            long_context_output_cost=item.long_context_output_cost,
                            # Prompt caching — standard context
                            cache_read_input_cost=item.cache_read_input_cost,
                            cache_write_input_cost=item.cache_write_input_cost,
                            # Prompt caching — long context
                            long_context_cache_read_input_cost=item.long_context_cache_read_input_cost,
                            long_context_cache_write_input_cost=item.long_context_cache_write_input_cost,
                            # Batch pricing
                            batch_input_cost=item.batch_input_cost,
                            batch_output_cost=item.batch_output_cost,
                            # Fine-tuning
                            training_cost=item.training_cost,
                            fine_tuned_input_cost=item.fine_tuned_input_cost,
                            fine_tuned_output_cost=item.fine_tuned_output_cost,
                            # Modality-specific costs
                            image_input_cost=item.image_input_cost,
                            image_output_cost=item.image_output_cost,
                            image_output_size=item.image_output_size,
                            audio_input_cost=item.audio_input_cost,
                            audio_output_cost=item.audio_output_cost,
                            transcription_cost=item.transcription_cost,
                            # Lifecycle
                            is_default=False,
                            is_active=True,
                            is_free=False,
                            priority=item.priority,
                            effective_date=_date.today(),
                            deprecated_date=None,
                            notes=item.notes,
                            source_url=item.source_url,
                        )
                        .on_conflict_do_nothing(constraint="model_pricing_model_id_provider_unique")
                    )

                    # 3. Enable the model
                    await db.execute(
                        update(Model).where(Model.model_id == model_id).values(is_enabled=True)
                    )

                    # 4. Clear any existing v1 default, then set this provider as default
                    await db.execute(
                        update(ModelPrice)
                        .where(ModelPrice.model_id == model_id)
                        .values(is_default=False)
                    )
                    await db.execute(
                        update(ModelPrice)
                        .where(
                            ModelPrice.model_id == model_id,
                            ModelPrice.provider == body.provider,
                        )
                        .values(
                            is_default=True,
                            prompt_usd_per_1k=effective_prompt_cost,
                            completion_usd_per_1k=effective_completion_cost,
                        )
                    )

                    # 4b. Clear any existing v2 default, then set this provider as default
                    await db.execute(
                        update(ModelPricing)
                        .where(ModelPricing.model_id == model_id)
                        .values(is_default=False)
                    )
                    await db.execute(
                        update(ModelPricing)
                        .where(
                            ModelPricing.model_id == model_id,
                            ModelPricing.provider == body.provider,
                            ModelPricing.is_active.is_(True),
                        )
                        .values(
                            is_default=True,
                            input_cost=prompt_usd_per_1k,
                            output_cost=completion_usd_per_1k,
                        )
                    )
                    is_default = True

                    await db.commit()
            except Exception as db_exc:  # noqa: BLE001
                logger.exception(
                    "test_models_db_error",
                    model_id=model_id,
                    provider=body.provider,
                    error=str(db_exc),
                )

        # ── Yield SSE event ────────────────────────────────────────────────
        event = {
            "model_id": model_id,
            "status": status,
            "latency_ms": latency_ms,
            "is_default": is_default,
            "error": error,
        }
        yield f"data: {json.dumps(event)}\n\n".encode()

    # Invalidate models + auto-router caches so GET /v1/models reflects new state immediately
    from app.models.cache import invalidate_models_cache

    await invalidate_models_cache()

    # Final summary event
    summary = {
        "type": "summary",
        "total": len(body.models),
        "passed": passed,
        "failed": failed,
        "is_dry_run": body.is_dry_run,
    }
    yield f"data: {json.dumps(summary)}\n\n".encode()
    yield b"data: [DONE]\n\n"


@router.post("/completions", summary="Test models against a provider and register results")
async def test_completions(
    body: TestModelsRequest,
    _: ControlPlaneIdentity = Depends(get_admin_user),  # noqa: B008
) -> StreamingResponse:
    """
    Test each model in the list against the specified provider using server-side
    credentials, then register the results in the DB.

    Streams SSE events — one per model — as they complete, followed by a summary.

    **SSE event format (per model)**
    ```json
    {"model_id": "anthropic/claude-3-haiku", "status": "pass", "latency_ms": 342,
     "is_default": true, "error": null}
    ```

    **SSE summary event**
    ```json
    {"type": "summary", "total": 5, "passed": 4, "failed": 1}
    ```

    **DB behaviour**
    - `models` row: inserted with `is_enabled=false` if new; set to `is_enabled=true` on pass
    - `model_prices` (v1) row: inserted with defaults if new; `is_default=true` set on pass
    - `model_pricing` (v2) row: inserted with full v2 fields if new; `is_default=true` set on pass
    - Existing rows are never overwritten on initial insert (ON CONFLICT DO NOTHING)

    **Image model example** (set `test_modality: "image"` for image-generation models):

        curl -X POST http://localhost:8000/test/completions \\
          -H "Content-Type: application/json" \\
          -d '{
            "provider": "openai",
            "is_dry_run": false,
            "image_prompt": "A red circle on a white background.",
            "models": [{
              "model_id": "openai/gpt-image-1",
              "provider_model_id": "gpt-image-1",
              "test_modality": "image",
              "modality": ["image"],
              "output_modalities": ["image"],
              "supports_completions_api": false,
              "pricing_unit": "per_image",
              "image_output_cost": 0.04
            }]
          }'

    **Minimal example** (all v2 fields use safe defaults):

        curl -X POST http://localhost:8000/test/completions \\
          -H "Content-Type: application/json" \\
          -d '{
            "provider": "openrouter",
            "is_dry_run": false,
            "models": [{
              "model_id": "anthropic/claude-3-haiku",
              "provider_model_id": "anthropic/claude-3-haiku",
              "input_token_cost_per_1k": 0.00025,
              "output_token_cost_per_1k": 0.00125
            }]
          }'

    **Full example** (all v2 fields explicit):

        curl -X POST http://localhost:8000/test/completions \\
          -H "Content-Type: application/json" \\
          -d '{
            "provider": "openrouter",
            "is_dry_run": false,
            "prompt": "Reply with just the word OK.",
            "timeout": 30,
            "models": [{
              "model_id": "anthropic/claude-3-haiku",
              "provider_model_id": "anthropic/claude-3-haiku",
              "input_token_cost_per_1k": 0.00025,
              "output_token_cost_per_1k": 0.00125,
              "pricing_unit": "per_1k_tokens",
              "currency": "USD",
              "modality": ["text"],
              "input_modalities": ["text"],
              "output_modalities": ["text"],
              "supports_thinking": false,
              "supports_completions_api": true,
              "supports_responses_api": false,
              "supports_embeddings": false,
              "supports_batching": true,
              "supports_tools": true,
              "supports_structured_output": true,
              "supports_system_prompt": true,
              "context_window": 200000,
              "request_cost": null,
              "standard_context_threshold": null,
              "long_context_input_cost": null,
              "long_context_output_cost": null,
              "cache_read_input_cost": 0.000003,
              "cache_write_input_cost": 0.0000375,
              "long_context_cache_read_input_cost": null,
              "long_context_cache_write_input_cost": null,
              "batch_input_cost": 0.000125,
              "batch_output_cost": 0.000625,
              "training_cost": null,
              "fine_tuned_input_cost": null,
              "fine_tuned_output_cost": null,
              "image_input_cost": null,
              "image_output_cost": null,
              "image_output_size": null,
              "audio_input_cost": null,
              "audio_output_cost": null,
              "transcription_cost": null,
              "priority": 1,
              "notes": "Standard claude-3-haiku pricing as of 2026-04",
              "source_url": "https://www.anthropic.com/pricing"
            }]
          }'
    """
    return StreamingResponse(
        _test_models_stream(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
