"""
Batch API router — proxies async batch processing to any provider that supports it.

Endpoints:
  POST   /v1/files                       upload a JSONL file (purpose=batch)
  GET    /v1/files/{file_id}             file metadata
  DELETE /v1/files/{file_id}             delete a file
  GET    /v1/files/{file_id}/content     download file contents (results JSONL)
  POST   /v1/batches                     create a batch job
  GET    /v1/batches                     list batch jobs (from MeshAPI DB — unified across providers)
  GET    /v1/batches/{batch_id}          get batch status
  POST   /v1/batches/{batch_id}/cancel   cancel a batch

Auth:    Authorization: Bearer rsk_<ULID>  (same as inference)
Routing: model-based, same as inference. The customer passes a model name
         (e.g. "openai/gpt-4o-mini"). MeshAPI resolves the provider from the
         model_prices table via resolve_routing() — the customer never specifies
         a provider. Any adapter that implements the Batch API methods works.
         Returns 501 if the resolved provider's adapter doesn't support batch.

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

Concurrent batch limit
-----------------------
Each owner may have at most 10 batches in a non-terminal state at any time.
POST /v1/batches returns 429 (batch_limit_exceeded) if this ceiling is hit.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
import json as _json

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_authenticated_key
from app.cache.rate_limiter import check_rate_limits
from app.config import settings
from app.db.engine import get_session_factory
from app.db.models import ApiKey, BatchFile, BatchJob, Model, ModelPrice, UsageEvent
from app.db.session import get_db_session
from app.exceptions import RouterVError, UnsupportedModelError
from app.providers.base import ProviderAdapter
from app.providers.key_resolver import resolve_upstream_key
from app.providers.registry import get_adapter, resolve_batch_routing
from app.usage.logger import _our_cost

router = APIRouter()
logger = structlog.get_logger()

_TERMINAL_STATUSES = {"completed", "failed", "cancelled", "expired"}
_MAX_ACTIVE_BATCHES = 10


def _provider_adapter(provider: str) -> ProviderAdapter:
    """
    Return a registered adapter for *provider* and verify it supports batch.
    Raises 503 if the provider is not registered, 501 if it doesn't implement batch.
    """
    from app.exceptions import ProviderNotAvailableError
    adapter = get_adapter(provider)  # raises ProviderNotAvailableError(503) if not registered
    # Smoke-test: confirm batch is supported before doing any upstream work.
    # get_batch is representative — if it's NotImplementedError, all batch ops are.
    if type(adapter).get_batch is ProviderAdapter.get_batch:
        raise RouterVError(
            f"Provider '{provider}' does not support the Batch API.",
            status_code=501,
            error_code="not_implemented",
        )
    return adapter


async def _resolve_canonical_model(raw_model: str, db: AsyncSession) -> str:
    """
    Resolve a raw model string from the JSONL body.model to a canonical model_id.

    Lookup order:
      1. Exact match on model_prices.model_id  (e.g. "openai/gpt-4o-mini")
      2. Match on model_prices.provider_model_id  (e.g. "gpt-4o-mini-2024-07-18")
    Both paths require models.is_enabled=True.

    Raises UnsupportedModelError if neither lookup finds a row.
    """
    # 1. Exact model_id match
    result = await db.execute(
        select(ModelPrice.model_id)
        .join(Model, Model.model_id == ModelPrice.model_id)
        .where(ModelPrice.model_id == raw_model, Model.is_enabled.is_(True))
        .limit(1)
    )
    row = result.one_or_none()
    if row is not None:
        return row.model_id

    # 2. provider_model_id match (bare upstream IDs like "gpt-4o-mini-2024-07-18")
    result = await db.execute(
        select(ModelPrice.model_id)
        .join(Model, Model.model_id == ModelPrice.model_id)
        .where(ModelPrice.provider_model_id == raw_model, Model.is_enabled.is_(True))
        .limit(1)
    )
    row = result.one_or_none()
    if row is not None:
        return row.model_id

    raise UnsupportedModelError(raw_model)


async def _resolve_and_map_models(
    requests: list["BatchRequestItem"], db: AsyncSession
) -> tuple[str, str, dict[str, str]]:
    """
    Validate all models across the request list and return a replacement map.

    All requests must use the same model — providers (e.g. OpenAI) enforce
    single-model batches and reject mixed-model files at submission time.

    For each distinct body.model value:
      1. Resolves to a canonical model_id via _resolve_canonical_model.
      2. Verifies supports_batching=True on the model_prices row.
      3. Looks up the upstream model ID — uses provider_model_id if set,
         falls back to the canonical model_id.

    Returns:
      (canonical_model, provider, {raw_model -> upstream_model_id})

    The upstream_model_id map is used to rewrite body.model in the JSONL
    sent to the provider so the provider receives its own native model ID.

    Raises:
      400 invalid_batch_file              — no body.model found on any request
      404 model_not_found                 — a model is unknown or disabled
      400 model_not_supported_for_batching — model exists but supports_batching=False
      400 mixed_models                    — requests use more than one model
    """
    seen: dict[str, str] = {}  # raw_model -> upstream_model_id
    first_canonical: str | None = None
    resolved_provider: str | None = None

    for req in requests:
        raw = (req.body or {}).get("model", "")
        if not raw or raw in seen:
            continue
        canonical = await _resolve_canonical_model(raw, db)

        # All requests must target the same model.
        if first_canonical is None:
            first_canonical = canonical
        elif canonical != first_canonical:
            raise RouterVError(
                f"Batch file contains multiple models ('{first_canonical}' and '{canonical}'). "
                "All requests in a batch must use the same model.",
                status_code=400,
                error_code="mixed_models",
            )

        provider, provider_model_id, _ = await resolve_batch_routing(canonical, db)

        # Enforce the supports_batching capability flag.
        sb_result = await db.execute(
            select(ModelPrice.supports_batching)
            .where(ModelPrice.model_id == canonical, ModelPrice.provider == provider)
            .limit(1)
        )
        sb_row = sb_result.one_or_none()
        if not sb_row or not sb_row.supports_batching:
            raise RouterVError(
                f"Model '{raw}' does not support the Batch API. "
                "Enable supports_batching in model_prices to use this model in a batch.",
                status_code=400,
                error_code="model_not_supported_for_batching",
            )

        upstream_id = provider_model_id or canonical
        seen[raw] = upstream_id
        resolved_provider = provider

    if not seen:
        raise RouterVError(
            "Each request must include a body.model field.",
            status_code=400,
            error_code="invalid_batch_file",
        )

    return first_canonical, resolved_provider, seen  # type: ignore[return-value]


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
    adapter: ProviderAdapter,
    upstream_key: str,
    usage_event_id: uuid.UUID | None = None,
    canonical_model: str | None = None,
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

    # Delegate output parsing to the adapter — each provider knows its own
    # output format and normalizes model names to match model_prices keys.
    try:
        results = adapter.parse_batch_results(content)
    except Exception as exc:
        logger.error("batch_sync_usage_parse_failed", batch_id=batch_id, error=str(exc))
        if usage_event_id:
            await _mark_usage_event_terminal(
                usage_event_id, "error", error_code="batch_parse_failed"
            )
        return

    # Build a per-item canonical model cache: versioned provider ID → canonical.
    # e.g. "openai/gpt-4.1-2025-04-14" → "openai/gpt-4.1"
    # Avoids a DB round-trip for every item when many share the same model.
    _canonical_cache: dict[str, str] = {}

    async def _resolve_item_model(raw: str) -> str:
        """Resolve a versioned provider model ID to a canonical model_prices.model_id."""
        if raw in _canonical_cache:
            return _canonical_cache[raw]
        resolved = raw
        async with get_session_factory()() as s:
            from app.db.models import ModelPrice as _MP
            # 1. Exact model_id match (unlikely for versioned IDs, but cheap to try)
            r = await s.execute(
                select(_MP.model_id).where(_MP.model_id == raw).limit(1)
            )
            row = r.one_or_none()
            if row:
                resolved = row.model_id
            else:
                # 2. provider_model_id match — strip provider prefix if present
                #    "openai/gpt-4.1-2025-04-14" → "gpt-4.1-2025-04-14"
                provider_part = raw.split("/", 1)[-1] if "/" in raw else raw
                r = await s.execute(
                    select(_MP.model_id).where(_MP.provider_model_id == provider_part).limit(1)
                )
                row = r.one_or_none()
                if row:
                    resolved = row.model_id
        _canonical_cache[raw] = resolved
        return resolved

    for item in results:
        if not item.get("success"):
            skipped += 1
            continue

        prompt_tokens: int = item.get("prompt_tokens") or 0
        completion_tokens: int = item.get("completion_tokens") or 0
        cached_tokens: int = item.get("cached_tokens") or 0
        raw_model: str = item.get("model") or ""

        if prompt_tokens or completion_tokens:
            billing_model = await _resolve_item_model(raw_model) if raw_model else canonical_model
            if not billing_model:
                billing_model = canonical_model
            line_cost = await _our_cost(billing_model, prompt_tokens, completion_tokens) if billing_model else None
            if line_cost is not None:
                total_cost += line_cost
            else:
                errors += 1

        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        total_cached_tokens += cached_tokens
        logged += 1

    # Apply account-level discount to the aggregated total.
    if total_cost > 0:
        try:
            from app.usage.balance import get_active_discount
            async with get_session_factory()() as disc_session:
                discount_pct = await get_active_discount(owner, "batch", disc_session)
            if discount_pct:
                total_cost = (total_cost * (1 - discount_pct / 100)).quantize(
                    Decimal("0.00000001")
                )
        except Exception as exc:
            logger.warning(
                "batch_discount_lookup_failed", owner=owner, batch_id=batch_id, error=str(exc)
            )

    if usage_event_id is not None:
        await _mark_usage_event_terminal(
            usage_event_id,
            "success",
            prompt_tokens=total_prompt_tokens or None,
            completion_tokens=total_completion_tokens or None,
            cached_tokens=total_cached_tokens or None,
            cost_usd=total_cost if total_cost > 0 else None,
        )

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
    adapter: ProviderAdapter,
    upstream_key: str,
    db: AsyncSession,
) -> None:
    """
    If the batch just reached a terminal state and hasn't been synced yet,
    mark it synced in the DB and spawn the appropriate background task.

    Sets usage_synced=True before spawning to prevent races.
    """
    new_status = batch.get("status", job.status)
    output_file_id = batch.get("output_file_id")

    job.status = new_status
    if output_file_id and not job.output_file_id:
        job.output_file_id = output_file_id

    if new_status == "completed" and not job.usage_synced:
        job.usage_synced = True
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        asyncio.create_task(
            _sync_usage(batch, job.owner, str(job.key_id), adapter, upstream_key, job.usage_event_id, job.model)
        )
    elif new_status in _TERMINAL_STATUSES and not job.usage_synced:
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

class BatchRequestItem(BaseModel):
    custom_id: str
    method: str = "POST"
    url: str = "/v1/chat/completions"
    body: dict


class UploadBatchFileRequest(BaseModel):
    purpose: str = "batch"
    requests: list[BatchRequestItem] = Field(..., min_length=1)


@router.post("/v1/files")
async def upload_file(
    body: UploadBatchFileRequest,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Prepare a batch file from a JSON array of requests.

    Accepts a JSON body with a `requests` array — no JSONL required.
    The backend converts the array to JSONL, validates all models resolve
    to the same provider, and uploads to the upstream provider.
    Raises 400 (mixed_providers) if requests span multiple providers.
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
    model, provider, model_map = await _resolve_and_map_models(body.requests, db)

    # Build JSONL with body.model replaced by the upstream provider model ID
    # so the provider receives its own native model string (e.g. "gpt-4o-mini-2024-07-18").
    lines = []
    for req in body.requests:
        d = req.model_dump()
        raw_model = d["body"].get("model", "")
        if raw_model in model_map:
            d["body"]["model"] = model_map[raw_model]
        lines.append(_json.dumps(d))
    content = "\n".join(lines).encode()

    adapter = _provider_adapter(provider)
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)
    result = await adapter.upload_file(
        content,
        "batch.jsonl",
        body.purpose,
        api_key=upstream_key,
    )
    db.add(BatchFile(
        file_id=result["id"],
        owner=key.owner,
        key_id=key.id,
        model=model,
        provider=provider,
    ))
    await db.commit()
    logger.info(
        "batch_file_uploaded",
        owner=key.owner,
        file_id=result.get("id"),
        purpose=body.purpose,
        model=model,
        provider=provider,
    )
    return result


@router.get("/v1/files/{file_id}")
async def get_file(
    file_id: str,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """Get metadata for a previously uploaded file."""
    provider = await _provider_from_file_id(file_id, db)
    adapter = _provider_adapter(provider)
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)
    return await adapter.get_file(file_id, api_key=upstream_key)


@router.delete("/v1/files/{file_id}")
async def delete_file(
    file_id: str,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a file from provider storage."""
    provider = await _provider_from_file_id(file_id, db)
    adapter = _provider_adapter(provider)
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)
    result = await adapter.delete_file(file_id, api_key=upstream_key)
    logger.info("batch_file_deleted", owner=key.owner, file_id=file_id, provider=provider)
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

    If this file_id is a known batch output file, usage sync is triggered
    here so billing is guaranteed even when the customer skips polling.
    """
    # Check whether this file_id is a batch output we need to bill.
    result = await db.execute(
        select(BatchJob).where(BatchJob.output_file_id == file_id)
    )
    job = result.scalar_one_or_none()

    provider = job.provider if job else "openai"
    adapter = _provider_adapter(provider)
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)

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


async def _provider_from_file_id(file_id: str, db: AsyncSession) -> str:
    """
    Derive the provider for a file_id.

    Lookup order:
      1. batch_files (files uploaded via POST /v1/files after migration 0037)
      2. batch_jobs input_file_id / output_file_id (backward compat + output files)
      3. "openai" fallback for files predating both tables.
    """
    result = await db.execute(
        select(BatchFile.provider).where(BatchFile.file_id == file_id).limit(1)
    )
    row = result.one_or_none()
    if row is not None:
        return row.provider

    result = await db.execute(
        select(BatchJob.provider).where(
            or_(
                BatchJob.input_file_id == file_id,
                BatchJob.output_file_id == file_id,
            )
        ).limit(1)
    )
    row = result.one_or_none()
    return row.provider if row else "openai"


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

    Model and provider are derived from the input_file_id — the file must
    have been uploaded via POST /v1/files, which resolves and stores them.
    `endpoint` must be `/v1/chat/completions`. `completion_window` is `"24h"`.

    Returns 404 if input_file_id was not uploaded through this account.
    Returns 429 (batch_limit_exceeded) if the owner already has 10 or more
    batches in a non-terminal state.
    Returns 501 (not_implemented) if the resolved provider doesn't support batch.
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
            "Wait for some to complete before creating new ones.",
            status_code=429,
            error_code="batch_limit_exceeded",
        )

    file_row_result = await db.execute(
        select(BatchFile).where(
            BatchFile.file_id == body.input_file_id,
            BatchFile.owner == key.owner,
        )
    )
    batch_file = file_row_result.scalar_one_or_none()
    if batch_file is None:
        raise RouterVError(
            f"File '{body.input_file_id}' not found. "
            "Upload the file via POST /v1/files before creating a batch.",
            status_code=404,
            error_code="file_not_found",
        )

    model = batch_file.model
    provider = batch_file.provider
    adapter = _provider_adapter(provider)
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)

    result = await adapter.create_batch(
        body.input_file_id,
        body.endpoint,
        body.completion_window,
        body.metadata,
        api_key=upstream_key,
    )

    event = UsageEvent(
        key_id=key.id,
        request_id=result["id"],
        model=model,
        provider=provider,
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
    await db.flush()

    job = BatchJob(
        batch_id=result["id"],
        owner=key.owner,
        key_id=key.id,
        model=model,
        provider=provider,
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
        model=model,
        provider=provider,
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
    """
    List batch jobs for the authenticated key's owner.

    Returns MeshAPI's own BatchJob records (unified view across all providers)
    in the OpenAI list format: `{"object": "list", "data": [...], "has_more": bool}`.
    Supports cursor-based pagination via `after` (batch_id) and `limit`.
    """
    query = (
        select(BatchJob)
        .where(BatchJob.owner == key.owner)
        .order_by(BatchJob.created_at.desc())
        .limit(limit + 1)
    )
    if after:
        # Cursor: find the created_at of the `after` batch_id, then page from there.
        cursor_result = await db.execute(
            select(BatchJob.created_at).where(BatchJob.batch_id == after)
        )
        cursor_row = cursor_result.one_or_none()
        if cursor_row:
            query = query.where(BatchJob.created_at < cursor_row.created_at)

    rows_result = await db.execute(query)
    rows = rows_result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "object": "list",
        "data": [_batch_job_to_dict(j) for j in page],
        "has_more": has_more,
        "first_id": page[0].batch_id if page else None,
        "last_id": page[-1].batch_id if page else None,
    }


@router.get("/v1/batches/{batch_id}")
async def get_batch(
    batch_id: str,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get batch status from the upstream provider.
    Usage logging and billing fire automatically on the first terminal observation.
    """
    db_result = await db.execute(select(BatchJob).where(BatchJob.batch_id == batch_id))
    job = db_result.scalar_one_or_none()

    provider = job.provider if job else "openai"
    adapter = _provider_adapter(provider)
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)

    batch = await adapter.get_batch(batch_id, api_key=upstream_key)

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
    db_result = await db.execute(select(BatchJob).where(BatchJob.batch_id == batch_id))
    job = db_result.scalar_one_or_none()

    provider = job.provider if job else "openai"
    adapter = _provider_adapter(provider)
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)

    result = await adapter.cancel_batch(batch_id, api_key=upstream_key)

    if job:
        job.status = result.get("status", "cancelling")
        await db.commit()

    logger.info("batch_cancelled", owner=key.owner, batch_id=batch_id, provider=provider)
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _batch_job_to_dict(job: BatchJob) -> dict:
    """Serialize a BatchJob row into the OpenAI batch object shape."""
    return {
        "id": job.batch_id,
        "object": "batch",
        "endpoint": "/v1/chat/completions",
        "input_file_id": job.input_file_id,
        "output_file_id": job.output_file_id,
        "status": job.status,
        "model": job.model,
        "provider": job.provider,
        "created_at": int(job.created_at.timestamp()) if job.created_at else None,
        "completed_at": int(job.completed_at.timestamp()) if job.completed_at else None,
        "usage_synced": job.usage_synced,
    }
