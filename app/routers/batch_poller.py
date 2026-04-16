"""
Background poller for in-progress batch jobs.

Runs every 60 s, checks all non-terminal BatchJob rows, and triggers usage
sync + billing when a batch reaches a terminal state. This guarantees balance
deduction even if the customer never polls or downloads results after submitting.

Exposed as a single coroutine — `batch_poll_loop()` — intended to be wrapped
in an asyncio.Task from the app lifespan.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()

_POLL_INTERVAL = 10  # seconds


async def batch_poll_loop() -> None:
    from sqlalchemy import select

    from app.db.engine import get_session_factory
    from app.db.models import BatchJob
    from app.exceptions import ProviderNotAvailableError
    from app.providers.key_resolver import resolve_upstream_key
    from app.providers.registry import get_adapter
    from app.routers.batch import _TERMINAL_STATUSES, _mark_usage_event_terminal, _sync_usage

    while True:
        await asyncio.sleep(_POLL_INTERVAL)
        try:
            async with get_session_factory()() as session:
                result = await session.execute(
                    select(BatchJob).where(
                        BatchJob.status.notin_(list(_TERMINAL_STATUSES)),
                        BatchJob.usage_synced.is_(False),
                    )
                )
                pending = result.scalars().all()

            for job in pending:
                try:
                    try:
                        adapter = get_adapter(job.provider)
                    except ProviderNotAvailableError:
                        logger.warning(
                            "batch_poller_provider_unavailable",
                            provider=job.provider,
                            batch_id=job.batch_id,
                        )
                        continue

                    async with get_session_factory()() as session:
                        upstream_key = await resolve_upstream_key(
                            owner=job.owner, provider=job.provider, db=session
                        )
                        batch = await adapter.get_batch(job.batch_id, api_key=upstream_key)
                        new_status = batch.get("status", job.status)
                        output_file_id = batch.get("output_file_id")

                        # Refresh inside this session to avoid stale state.
                        db_result = await session.execute(
                            select(BatchJob).where(BatchJob.batch_id == job.batch_id)
                        )
                        db_job = db_result.scalar_one_or_none()
                        if not db_job or db_job.usage_synced:
                            continue

                        db_job.status = new_status
                        if output_file_id and not db_job.output_file_id:
                            db_job.output_file_id = output_file_id

                        if new_status == "completed":
                            db_job.usage_synced = True
                            db_job.completed_at = datetime.now(timezone.utc)
                            await session.commit()
                            asyncio.create_task(
                                _sync_usage(
                                    batch,
                                    job.owner,
                                    str(job.key_id),
                                    adapter,
                                    upstream_key,
                                    db_job.usage_event_id,
                                    db_job.model,
                                )
                            )
                            logger.info(
                                "batch_poller_synced",
                                batch_id=job.batch_id,
                                owner=job.owner,
                                provider=job.provider,
                            )
                        elif new_status in _TERMINAL_STATUSES:
                            db_job.usage_synced = True
                            await session.commit()
                            if db_job.usage_event_id is not None:
                                asyncio.create_task(
                                    _mark_usage_event_terminal(
                                        db_job.usage_event_id,
                                        "error",
                                        error_code=f"batch_{new_status}",
                                    )
                                )
                        else:
                            await session.commit()

                except Exception as exc:
                    logger.warning(
                        "batch_poller_job_failed",
                        batch_id=job.batch_id,
                        error=str(exc),
                    )

        except Exception as exc:
            logger.warning("batch_poll_loop_error", error=str(exc))
