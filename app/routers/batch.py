"""
Batch API router — proxies OpenAI Batch + Files API.

Endpoints:
  POST   /v1/files                       upload a JSONL file (purpose=batch)
  GET    /v1/files/{file_id}             file metadata
  DELETE /v1/files/{file_id}             delete a file
  GET    /v1/files/{file_id}/content     download file contents (results JSONL)
  POST   /v1/batches                     create a batch job
  GET    /v1/batches                     list batch jobs
  GET    /v1/batches/{batch_id}          get batch status
  POST   /v1/batches/{batch_id}/cancel   cancel a batch

Auth:    Authorization: Bearer rsk_<ULID>  (same as inference)
Provider: openai direct only — raise 503 if OPENAI_API_KEY is not configured.
Rate limits: applied on write operations (POST /v1/files, POST /v1/batches).

Usage logging + billing
-----------------------
On POST /v1/batches a UsageEvent row is created immediately with status="pending"
and all token fields null. Its UUID is stored in batch_jobs.usage_event_id.

When the batch completes the output JSONL is downloaded, tokens are aggregated
across all successful requests, cost is calculated, and the UsageEvent row is
updated (status="success", token counts, cost_usd). Balance is deducted once.
For failed/cancelled/expired batches the event is updated to status="error".

This update happens via three paths, in priority order:

  1. GET /v1/batches/{batch_id}     — fires on first completed observation.
  2. GET /v1/files/{file_id}/content — fires if customer skips further polling
                                       and downloads directly.
  3. Background poller (main.py)    — fires every 60 s for any batch that is
                                       still in-progress in the DB; guarantees
                                       billing even if the customer never
                                       interacts with MeshAPI again.

The batch_jobs.usage_synced flag (DB) is the single source of truth for
idempotency — set to True before spawning the task so duplicate triggers never
double-bill.

Concurrent batch limit
-----------------------
Each owner may have at most 10 batches in a non-terminal state at any time.
POST /v1/batches returns 429 (batch_limit_exceeded) if this ceiling is hit.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, Form, Query, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_authenticated_key
from app.cache.rate_limiter import check_rate_limits
from app.config import settings
from app.db.engine import get_session_factory
from app.db.models import ApiKey, BatchJob, UsageEvent
from app.db.session import get_db_session
from app.exceptions import ProviderNotAvailableError, RouterVError
from app.providers.key_resolver import resolve_upstream_key
from app.providers.openai_direct import OpenAIDirectAdapter
from app.usage.logger import _our_cost

router = APIRouter()
logger = structlog.get_logger()

_PROVIDER = "openai"

_TERMINAL_STATUSES = {"completed", "failed", "cancelled", "expired"}

_MAX_ACTIVE_BATCHES = 10


def _get_adapter() -> OpenAIDirectAdapter:
    try:
        return OpenAIDirectAdapter.get()
    except RuntimeError as exc:
        raise ProviderNotAvailableError(_PROVIDER) from exc


# ── Internal: usage sync ──────────────────────────────────────────────────────

async def _mark_usage_event_terminal(
    usage_event_id: uuid.UUID,
    status: str,  # "success" | "error"
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    cached_tokens: int | None = None,
    cost_usd: Decimal | None = None,
    error_code: str | None = None,
) -> None:
    """Update the pending UsageEvent row created at batch submission time."""
    try:
        async with get_session_factory()() as session:
            result = await session.execute(
                select(UsageEvent).where(UsageEvent.id == usage_event_id)
            )
            event = result.scalar_one_or_none()
            if event and event.status == "pending":
                event.status = status
                event.prompt_tokens = prompt_tokens
                event.completion_tokens = completion_tokens
                event.total_tokens = (
                    (prompt_tokens or 0) + (completion_tokens or 0) or None
                )
                event.cached_tokens = cached_tokens
                event.cost_usd = cost_usd
                event.error_code = error_code
                await session.commit()
    except Exception as exc:
        logger.error(
            "batch_usage_event_update_failed",
            usage_event_id=str(usage_event_id),
            error=str(exc),
        )


async def _sync_usage(
    batch: dict,
    owner: str,
    key_id: str,
    adapter: OpenAIDirectAdapter,
    upstream_key: str,
    usage_event_id: uuid.UUID | None = None,
) -> None:
    """
    Download the batch output file, aggregate tokens + cost across all
    successful requests, update the pending UsageEvent row, and deduct balance.

    Runs as a background task — errors are swallowed so they never block the
    caller or the poller.
    """
    batch_id = batch.get("id", "unknown")
    output_file_id = batch.get("output_file_id")
    if not output_file_id:
        logger.warning("batch_sync_usage_no_output_file", batch_id=batch_id, owner=owner)
        if usage_event_id:
            await _mark_usage_event_terminal(
                usage_event_id, "error", error_code="batch_no_output_file"
            )
        return

    try:
        content = await adapter.get_file_content(output_file_id, api_key=upstream_key)
    except Exception as exc:
        logger.error("batch_sync_usage_download_failed", batch_id=batch_id, error=str(exc))
        if usage_event_id:
            await _mark_usage_event_terminal(
                usage_event_id, "error", error_code="batch_download_failed"
            )
        return

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cached_tokens = 0
    total_cost = Decimal("0")
    logged = skipped = errors = 0

    for raw_line in content.decode(errors="replace").strip().splitlines():
        if not raw_line.strip():
            continue
        try:
            obj = json.loads(raw_line)
            response = obj.get("response") or {}
            status_code = response.get("status_code")

            if status_code != 200:
                skipped += 1
                continue

            body = response.get("body") or {}
            usage = body.get("usage") or {}
            prompt_tokens: int = usage.get("prompt_tokens") or 0
            completion_tokens: int = usage.get("completion_tokens") or 0
            cached_tokens: int = (
                (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
            )

            # OpenAI returns the resolved model name (e.g. "gpt-4o-mini-2024-07-18").
            # Prepend "openai/" so it matches our model_prices table key.
            raw_model: str = body.get("model", "")
            model = f"openai/{raw_model}" if raw_model and "/" not in raw_model else raw_model

            if prompt_tokens or completion_tokens:
                line_cost = await _our_cost(model, prompt_tokens, completion_tokens)
                if line_cost is not None:
                    total_cost += line_cost

            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_cached_tokens += cached_tokens
            logged += 1

        except Exception as exc:
            logger.warning(
                "batch_sync_usage_parse_error",
                owner=owner,
                batch_id=batch_id,
                error=str(exc),
                line_preview=raw_line[:120],
            )
            errors += 1

    # Apply account-level discount to the aggregated total.
    if total_cost > 0:
        try:
            from app.usage.balance import get_active_discount
            async with get_session_factory()() as disc_session:
                discount_pct = await get_active_discount(owner, "openai/batch", disc_session)
            if discount_pct:
                total_cost = (total_cost * (1 - discount_pct / 100)).quantize(
                    Decimal("0.00000001")
                )
        except Exception as exc:
            logger.warning(
                "batch_discount_lookup_failed", owner=owner, batch_id=batch_id, error=str(exc)
            )

    # Update the pending UsageEvent row with aggregated results.
    if usage_event_id is not None:
        await _mark_usage_event_terminal(
            usage_event_id,
            "success",
            prompt_tokens=total_prompt_tokens or None,
            completion_tokens=total_completion_tokens or None,
            cached_tokens=total_cached_tokens or None,
            cost_usd=total_cost if total_cost > 0 else None,
        )

    # Deduct balance once for the whole batch.
    if total_cost > 0:
        from app.usage.balance import deduct_balance
        await deduct_balance(owner, total_cost)

    logger.info(
        "batch_usage_synced",
        owner=owner,
        batch_id=batch_id,
        logged=logged,
        skipped=skipped,
        errors=errors,
        total_cost=str(total_cost),
    )


async def _maybe_sync(
    batch: dict,
    job: BatchJob,
    adapter: OpenAIDirectAdapter,
    upstream_key: str,
    db: AsyncSession,
) -> None:
    """
    If the batch just reached a terminal state and hasn't been synced yet,
    mark it synced in the DB and spawn the appropriate background task.

    Must be called inside an active DB session with the job already loaded.
    Sets usage_synced=True before spawning the task to prevent races.
    """
    new_status = batch.get("status", job.status)
    output_file_id = batch.get("output_file_id")

    # Always keep the DB row current.
    job.status = new_status
    if output_file_id and not job.output_file_id:
        job.output_file_id = output_file_id

    if new_status == "completed" and not job.usage_synced:
        job.usage_synced = True
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        asyncio.create_task(
            _sync_usage(batch, job.owner, str(job.key_id), adapter, upstream_key, job.usage_event_id)
        )
    elif new_status in _TERMINAL_STATUSES and not job.usage_synced:
        # Failed / cancelled / expired — no charge; mark event as error.
        job.usage_synced = True
        await db.commit()
        if job.usage_event_id is not None:
            asyncio.create_task(
                _mark_usage_event_terminal(
                    job.usage_event_id,
                    "error",
                    error_code=f"batch_{new_status}",
                )
            )
    else:
        await db.commit()


# ── Files ─────────────────────────────────────────────────────────────────────

@router.post("/v1/files")
async def upload_file(
    file: UploadFile,
    purpose: str = Form(...),
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """Upload a JSONL file to OpenAI. Returns a file object with an `id` for use in POST /v1/batches."""
    await check_rate_limits(
        key_id=str(key.id),
        rpm_limit=key.rpm_limit,
        rpd_limit=key.rpd_limit,
        default_rpm=settings.default_rpm,
        default_rpd=settings.default_rpd,
        max_rpm=settings.max_rpm,
        max_rpd=settings.max_rpd,
    )
    adapter = _get_adapter()
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=_PROVIDER, db=db)
    content = await file.read()
    result = await adapter.upload_file(
        content,
        file.filename or "batch.jsonl",
        purpose,
        api_key=upstream_key,
    )
    logger.info("batch_file_uploaded", owner=key.owner, file_id=result.get("id"), purpose=purpose)
    return result


@router.get("/v1/files/{file_id}")
async def get_file(
    file_id: str,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """Get metadata for a previously uploaded file."""
    adapter = _get_adapter()
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=_PROVIDER, db=db)
    return await adapter.get_file(file_id, api_key=upstream_key)


@router.delete("/v1/files/{file_id}")
async def delete_file(
    file_id: str,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a file from OpenAI storage."""
    adapter = _get_adapter()
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=_PROVIDER, db=db)
    result = await adapter.delete_file(file_id, api_key=upstream_key)
    logger.info("batch_file_deleted", owner=key.owner, file_id=file_id)
    return result


@router.get("/v1/files/{file_id}/content")
async def get_file_content(
    file_id: str,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Download raw file bytes.
    Primary use-case: fetch batch output JSONL after a batch completes
    (`batch.output_file_id`).

    If this file_id is a known batch output file (output_file_id stored in
    batch_jobs), usage sync is triggered here so billing is guaranteed even
    when the customer skips polling entirely.
    """
    adapter = _get_adapter()
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=_PROVIDER, db=db)

    # Check whether this file_id is a batch output we need to bill.
    result = await db.execute(
        select(BatchJob).where(BatchJob.output_file_id == file_id)
    )
    job = result.scalar_one_or_none()
    if job and not job.usage_synced:
        try:
            batch = await adapter.get_batch(job.batch_id, api_key=upstream_key)
            await _maybe_sync(batch, job, adapter, upstream_key, db)
        except Exception as exc:
            logger.warning(
                "batch_file_content_sync_failed",
                file_id=file_id,
                batch_id=job.batch_id,
                error=str(exc),
            )

    content = await adapter.get_file_content(file_id, api_key=upstream_key)
    return Response(content=content, media_type="application/octet-stream")


# ── Batches ───────────────────────────────────────────────────────────────────

class CreateBatchRequest(BaseModel):
    input_file_id: str
    endpoint: str
    completion_window: str
    metadata: dict | None = None


@router.post("/v1/batches")
async def create_batch(
    body: CreateBatchRequest,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a batch job.

    `endpoint` must be `/v1/chat/completions` (or another OpenAI-supported batch endpoint).
    `completion_window` is `"24h"`.

    Returns 429 (batch_limit_exceeded) if the owner already has
    10 or more batches in a non-terminal state.
    """
    await check_rate_limits(
        key_id=str(key.id),
        rpm_limit=key.rpm_limit,
        rpd_limit=key.rpd_limit,
        default_rpm=settings.default_rpm,
        default_rpd=settings.default_rpd,
        max_rpm=settings.max_rpm,
        max_rpd=settings.max_rpd,
    )

    # Enforce concurrent batch limit before hitting OpenAI.
    count_result = await db.execute(
        select(func.count()).select_from(BatchJob).where(
            BatchJob.owner == key.owner,
            BatchJob.status.notin_(list(_TERMINAL_STATUSES)),
        )
    )
    active_count = count_result.scalar_one()
    if active_count >= _MAX_ACTIVE_BATCHES:
        raise RouterVError(
            f"You have {active_count} batch jobs currently processing. "
            f"Wait for some to complete before creating new ones.",
            status_code=429,
            error_code="batch_limit_exceeded",
        )

    adapter = _get_adapter()
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=_PROVIDER, db=db)
    result = await adapter.create_batch(
        body.input_file_id,
        body.endpoint,
        body.completion_window,
        body.metadata,
        api_key=upstream_key,
    )

    # Create a pending UsageEvent immediately so the batch is visible in usage
    # history from the moment it's submitted. The row is updated with token
    # counts and cost when the batch completes.
    event = UsageEvent(
        key_id=key.id,
        request_id=result["id"],  # batch_id doubles as request_id
        model="openai/batch",
        provider=_PROVIDER,
        template_id=None,
        stream=False,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        cached_tokens=None,
        cost_usd=None,
        latency_ms=None,
        status="pending",
        error_code=None,
    )
    db.add(event)
    await db.flush()  # populate event.id before inserting BatchJob

    # Record the batch so the poller and file-content endpoint can bill it.
    job = BatchJob(
        batch_id=result["id"],
        owner=key.owner,
        key_id=key.id,
        input_file_id=body.input_file_id,
        status=result.get("status", "validating"),
        usage_event_id=event.id,
    )
    db.add(job)
    await db.commit()

    logger.info(
        "batch_created",
        owner=key.owner,
        batch_id=result.get("id"),
        endpoint=body.endpoint,
        usage_event_id=str(event.id),
    )
    return result


@router.get("/v1/batches")
async def list_batches(
    after: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """List batch jobs. Supports cursor-based pagination via `after` and `limit`."""
    adapter = _get_adapter()
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=_PROVIDER, db=db)
    return await adapter.list_batches(after=after, limit=limit, api_key=upstream_key)


@router.get("/v1/batches/{batch_id}")
async def get_batch(
    batch_id: str,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get batch status. Poll until `status` is `completed` (or `failed`/`cancelled`).
    On completion, `output_file_id` contains the results file ID.

    Usage logging and billing fire automatically on the first terminal
    observation, guarded by batch_jobs.usage_synced.
    """
    adapter = _get_adapter()
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=_PROVIDER, db=db)
    batch = await adapter.get_batch(batch_id, api_key=upstream_key)

    result = await db.execute(
        select(BatchJob).where(BatchJob.batch_id == batch_id)
    )
    job = result.scalar_one_or_none()
    if job and not job.usage_synced and batch.get("status") in _TERMINAL_STATUSES:
        await _maybe_sync(batch, job, adapter, upstream_key, db)

    return batch


@router.post("/v1/batches/{batch_id}/cancel")
async def cancel_batch(
    batch_id: str,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """Cancel an in-progress batch. Partial results may still be available."""
    adapter = _get_adapter()
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=_PROVIDER, db=db)
    result = await adapter.cancel_batch(batch_id, api_key=upstream_key)

    # Update status in DB immediately.
    db_result = await db.execute(select(BatchJob).where(BatchJob.batch_id == batch_id))
    job = db_result.scalar_one_or_none()
    if job:
        job.status = result.get("status", "cancelling")
        await db.commit()

    logger.info("batch_cancelled", owner=key.owner, batch_id=batch_id)
    return result
