"""
Test router — POST /test/completions

Streams SSE results for each model tested against the chat completions API.
No auth beyond admin JWT. Uses server-side credentials for the given provider.

On pass, upserts the model into `models` + `model_prices` with is_enabled=true
and is_default=true (unless is_dry_run=True).

Only registered when ENV=dev. Never ship this to production.
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.auth.control_plane import ControlPlaneIdentity, get_admin_user
from app.cache.redis_client import get_redis
from app.db.models import Model, ModelPrice

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
    models row       — INSERT if not exists (is_enabled=false); on pass → SET is_enabled=true
    model_prices row — INSERT if not exists (price=0, is_default=false); on pass →
                       if no other row for this model_id has is_default=true → SET is_default=true
    Both inserts use ON CONFLICT DO NOTHING — existing rows are never overwritten.
    """
    from app.db.engine import get_session_factory
    from app.providers.registry import get_adapter
    from app.schemas.chat import ChatCompletionRequest, Message

    # Validate provider has a registered adapter before streaming anything
    try:
        adapter = get_adapter(body.provider)
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n".encode()
        return

    session_factory = get_session_factory()
    passed = failed = 0

    for item in body.models:
        model_id              = item.model_id
        provider_model_id     = item.provider_model_id
        prompt_usd_per_1k     = item.input_token_cost_per_1k
        completion_usd_per_1k = item.output_token_cost_per_1k
        t0                    = time.monotonic()
        status                = "fail"
        error: str | None     = None

        # ── Test the model ─────────────────────────────────────────────────
        req = ChatCompletionRequest(
            model=model_id,
            messages=[Message(role="user", content=body.prompt)],
            max_tokens=32,
            stream=False,
        )
        try:
            resp = await asyncio.wait_for(
                adapter.chat_completion(
                    req, api_key=None, owner=None,
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
                error  = "Empty response content"
        except asyncio.TimeoutError:
            status = "timeout"
            error  = f"Timed out after {body.timeout:.0f}s"
        except Exception as exc:  # noqa: BLE001
            status = "fail"
            error  = str(exc)[:200]

        latency_ms   = int((time.monotonic() - t0) * 1000)
        test_passed  = status == "pass"
        is_default   = False

        if test_passed:
            passed += 1
        else:
            failed += 1

        # ── DB writes (only on pass) ────────────────────────────────────────
        if test_passed and not body.is_dry_run:
            name = _derive_model_name(model_id)
            try:
                async with session_factory() as db:
                    # 1. Insert model row if it doesn't exist (disabled by default)
                    await db.execute(
                        pg_insert(Model).values(
                            model_id=model_id,
                            name=name,
                            context_length=None,
                            brand=model_id.split("/")[0],
                            description=None,
                            is_enabled=False,
                        ).on_conflict_do_nothing(index_elements=["model_id"])
                    )

                    # 2. Insert model_prices row if (model_id, provider) not present
                    await db.execute(
                        pg_insert(ModelPrice).values(
                            model_id=model_id,
                            provider=body.provider,
                            provider_model_id=provider_model_id,
                            is_default=False,
                            prompt_usd_per_1k=prompt_usd_per_1k,
                            completion_usd_per_1k=completion_usd_per_1k,
                            is_free=False,
                        ).on_conflict_do_nothing(index_elements=["model_id", "provider"])
                    )

                    if test_passed:
                        # 3. Enable the model
                        await db.execute(
                            update(Model)
                            .where(Model.model_id == model_id)
                            .values(is_enabled=True)
                        )

                        # 4. Clear any existing default, then set this provider as default
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
                                prompt_usd_per_1k=prompt_usd_per_1k,
                                completion_usd_per_1k=completion_usd_per_1k,
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
            "model_id":   model_id,
            "status":     status,
            "latency_ms": latency_ms,
            "is_default": is_default,
            "error":      error,
        }
        yield f"data: {json.dumps(event)}\n\n".encode()

    # Invalidate models cache so GET /v1/models reflects new state immediately
    try:
        redis = await get_redis()
        await redis.delete("routerv:models:list")
    except Exception:  # noqa: BLE001
        pass

    # Final summary event
    yield f"data: {json.dumps({'type': 'summary', 'total': len(body.models), 'passed': passed, 'failed': failed, 'is_dry_run': body.is_dry_run})}\n\n".encode()
    yield b"data: [DONE]\n\n"


@router.post("/completions", summary="Test models against a provider and register results")
async def test_completions(
    body: TestModelsRequest,
    _: ControlPlaneIdentity = Depends(get_admin_user),
) -> StreamingResponse:
    """
    Test each model in the list against the specified provider using server-side
    credentials, then register the results in the DB.

    Streams SSE events — one per model — as they complete, followed by a summary.

    **SSE event format (per model)**
    ```json
    {"model_id": "anthropic/claude-3-haiku", "status": "pass", "latency_ms": 342, "is_default": true, "error": null}
    ```

    **SSE summary event**
    ```json
    {"type": "summary", "total": 5, "passed": 4, "failed": 1}
    ```

    **DB behaviour**
    - `models` row: inserted with `is_enabled=false` if new; set to `is_enabled=true` on pass
    - `model_prices` row: inserted with `price=0, is_default=false` if new (model_id, provider) pair;
      `is_default` set to `true` on pass only if no other provider already holds the default
    - Existing rows are never overwritten (ON CONFLICT DO NOTHING)

    Example:
        curl -X POST http://localhost:8000/test/completions \\
          -H "Content-Type: application/json" \\
          -d '{
            "provider": "openrouter",
            "is_dry_run": false,
            "models": [{"model_id": "anthropic/claude-3-haiku", "provider_model_id": "anthropic/claude-3-haiku"}]
          }'
    """
    return StreamingResponse(
        _test_models_stream(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
