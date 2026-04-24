"""
Auto Router service — orchestration for model="auto" requests.

Call resolve_auto_model() from any inference router after the config resolver
has finalised body.model and before check_balance(). It returns an
AutoRouteResult whose resolved_model_id replaces "auto" in the request body.

Public helpers also imported by routers:
  _is_auto()                — detect the "auto" keyword
  _inject_auto_route_meta() — add x_auto_routed fields to a non-streaming response dict
  _auto_route_headers()     — build response headers for streaming responses
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auto_router.benchmark_classifier import (
    call_benchmark_classifier,
    parse_benchmark_response,
)
from app.auto_router.benchmarks import resolve_from_benchmark_category
from app.auto_router.classifier import call_classifier, parse_classifier_response
from app.auto_router.registry import ApiType, get_enabled_models
from app.config import settings
from app.exceptions import AutoRouterMisconfiguredError
from app.metrics import (
    AUTO_ROUTER_CLASSIFIER_LATENCY,
    AUTO_ROUTER_FALLBACK,
    AUTO_ROUTER_REQUESTS,
)

logger = structlog.get_logger()


@dataclass
class ClassifierUsage:
    """Token/cost usage for a single classifier LLM call."""

    model_id: str
    provider: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None


@dataclass
class AutoRouteResult:
    """Carries the resolved model ID, routing metadata, and classifier usage
    for response injection."""

    resolved_model_id: str
    used_fallback: bool = False
    fallback_reason: str | None = None
    classifier_usages: list[ClassifierUsage] = field(default_factory=list)


# ── Public helpers used by routers ────────────────────────────────────────────


def _is_auto(model: str | None) -> bool:
    """Return True when model="auto" (case-insensitive, whitespace-tolerant)."""
    return (model or "").strip().lower() == "auto"


def _inject_auto_route_meta(response_body: dict, result: AutoRouteResult) -> None:
    """Inject x_auto_routed metadata into a non-streaming response dict in-place."""
    response_body["x_auto_routed"] = True
    response_body["x_resolved_model_id"] = result.resolved_model_id
    if result.used_fallback:
        response_body["x_auto_routed_fallback"] = True
        response_body["x_auto_routed_fallback_reason"] = result.fallback_reason
    if result.classifier_usages:
        response_body["x_classifier_usage"] = [
            {
                "model_id": u.model_id,
                "prompt_tokens": u.prompt_tokens,
                "completion_tokens": u.completion_tokens,
            }
            for u in result.classifier_usages
        ]


def _auto_route_headers(result: AutoRouteResult) -> dict[str, str]:
    """Return HTTP headers to inject into a streaming response."""
    headers: dict[str, str] = {
        "X-Auto-Routed": "true",
        "X-Resolved-Model-Id": result.resolved_model_id,
    }
    if result.used_fallback:
        headers["X-Auto-Routed-Fallback"] = "true"
        headers["X-Auto-Routed-Fallback-Reason"] = result.fallback_reason or ""
    return headers


# ── Core routing logic ────────────────────────────────────────────────────────


async def resolve_auto_model(
    user_content: str,
    api_type: ApiType,
    *,
    db: AsyncSession,
    request_id: str = "",
    owner: str,
) -> AutoRouteResult:
    """
    Resolve model="auto" to a concrete model ID.

    Decision tree:
      1. Increment AUTO_ROUTER_REQUESTS counter.
      2. Fetch candidate models from registry (L1 Redis → L2 Redis → DB).
      3. Log auto_router.triggered.
      4. Empty registry → fallback immediately with reason "empty_registry".
      5. Call classifier LLM with asyncio.wait_for timeout.
      6. Parse + validate classifier response.
      7. Valid ID → log auto_router.model_resolved; return AutoRouteResult.
      8. Invalid/None → fallback with accurate reason from call_classifier.
      9. Validate fallback model → raise AutoRouterMisconfiguredError (HTTP 500) if missing.

    Parameters
    ----------
    user_content : pre-extracted text from the request (first user turn, embed input, etc.)
    api_type     : "completions" | "responses" | "embeddings" — controls model filtering
    request_id   : request ID for structured log correlation
    """
    AUTO_ROUTER_REQUESTS.inc()

    logger.info(
        "auto_router.triggered",
        request_id=request_id,
        api_type=api_type,
        mode="benchmark" if settings.auto_router_use_benchmarks else "registry",
    )

    if settings.auto_router_use_benchmarks:
        return await _resolve_via_benchmarks(
            user_content, api_type=api_type, db=db, request_id=request_id, owner=owner
        )

    # ── Registry path ─────────────────────────────────────────────────────────
    candidates = await get_enabled_models(api_type)
    valid_ids: set[str] = {c.model_id for c in candidates}

    logger.info(
        "auto_router.registry_candidates",
        request_id=request_id,
        candidate_model_count=len(candidates),
    )

    # ── Empty registry → skip classifiers, use default immediately ───────────
    if not candidates:
        AUTO_ROUTER_FALLBACK.labels(reason="empty_registry").inc()
        logger.warning(
            "auto_router.default_used",
            request_id=request_id,
            fallback_reason="empty_registry",
            default_model_id=settings.auto_router_default_model_id,
        )
        return _use_default("empty_registry", valid_ids, request_id, classifier_usages=[])

    classifier_usages: list[ClassifierUsage] = []

    # ── Primary classifier ────────────────────────────────────────────────────
    start = time.monotonic()
    raw, failure_reason, usage = await call_classifier(
        candidates,
        user_content,
        db=db,
        request_id=request_id,
        owner=owner,
    )
    elapsed_ms = int((time.monotonic() - start) * 1000)
    AUTO_ROUTER_CLASSIFIER_LATENCY.observe(elapsed_ms)
    if usage:
        classifier_usages.append(ClassifierUsage(**usage))

    resolved_id = parse_classifier_response(raw, valid_ids)

    if resolved_id is not None:
        logger.info(
            "auto_router.model_resolved",
            request_id=request_id,
            resolved_model_id=resolved_id,
            resolution_method="primary_classifier",
        )
        return AutoRouteResult(resolved_model_id=resolved_id, classifier_usages=classifier_usages)

    # ── Fallback classifier retry ─────────────────────────────────────────────
    fallback_classifier = settings.auto_router_fallback_model_id.strip()
    if fallback_classifier:
        logger.warning(
            "auto_router.primary_classifier_failed",
            request_id=request_id,
            reason=failure_reason or "invalid_response",
            retrying_with=fallback_classifier,
        )
        start = time.monotonic()
        raw2, failure_reason2, usage2 = await call_classifier(
            candidates,
            user_content,
            classifier_model_id=fallback_classifier,
            db=db,
            request_id=request_id,
            owner=owner,
        )
        elapsed_ms2 = int((time.monotonic() - start) * 1000)
        AUTO_ROUTER_CLASSIFIER_LATENCY.observe(elapsed_ms2)
        if usage2:
            classifier_usages.append(ClassifierUsage(**usage2))

        resolved_id2 = parse_classifier_response(raw2, valid_ids)

        if resolved_id2 is not None:
            logger.info(
                "auto_router.model_resolved",
                request_id=request_id,
                resolved_model_id=resolved_id2,
                resolution_method="fallback_classifier",
            )
            return AutoRouteResult(
                resolved_model_id=resolved_id2, classifier_usages=classifier_usages
            )

        failure_reason = failure_reason2 or "invalid_response"

    # ── Both classifiers failed → use configured default model ────────────────
    reason = failure_reason or "invalid_response"
    AUTO_ROUTER_FALLBACK.labels(reason=reason).inc()
    logger.warning(
        "auto_router.default_used",
        request_id=request_id,
        fallback_reason=reason,
        default_model_id=settings.auto_router_default_model_id,
    )
    return _use_default(reason, valid_ids, request_id, classifier_usages=classifier_usages)


async def _resolve_via_benchmarks(
    user_content: str,
    *,
    api_type: ApiType,
    db,
    request_id: str,
    owner: str,
) -> AutoRouteResult:
    """
    Benchmark routing path.

    1. Call benchmark classifier → raw "CATEGORY,MODE" response.
    2. Parse → (category, mode).
    3. resolve_from_benchmark_category(category, mode) → model_id.
    4. Return AutoRouteResult on success.
    5. Retry with fallback classifier on any failure.
    6. Use configured default if both classifiers fail.
    """
    classifier_usages: list[ClassifierUsage] = []

    async def _classify(classifier_model_id: str | None = None):
        start = time.monotonic()
        raw, failure_reason, usage = await call_benchmark_classifier(
            user_content,
            db=db,
            classifier_model_id=classifier_model_id,
            request_id=request_id,
            owner=owner,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        AUTO_ROUTER_CLASSIFIER_LATENCY.observe(elapsed_ms)
        if usage:
            classifier_usages.append(ClassifierUsage(**usage))
        return raw, failure_reason

    # ── Primary classifier ────────────────────────────────────────────────────
    raw, failure_reason = await _classify()
    category, mode = parse_benchmark_response(raw)

    if category:
        model_id = resolve_from_benchmark_category(
            category, mode, responses_api=(api_type == "responses")
        )
        if model_id:
            logger.info(
                "auto_router.model_resolved",
                request_id=request_id,
                resolved_model_id=model_id,
                resolution_method="benchmark_primary",
                category=category,
                mode=mode,
            )
            return AutoRouteResult(resolved_model_id=model_id, classifier_usages=classifier_usages)

    # ── Fallback classifier ───────────────────────────────────────────────────
    fallback_classifier = settings.auto_router_fallback_model_id.strip()
    if fallback_classifier:
        logger.warning(
            "auto_router.primary_classifier_failed",
            request_id=request_id,
            reason=failure_reason or "invalid_response",
            retrying_with=fallback_classifier,
        )
        raw2, failure_reason2 = await _classify(fallback_classifier)
        category2, mode2 = parse_benchmark_response(raw2)

        if category2:
            model_id2 = resolve_from_benchmark_category(
                category2, mode2, responses_api=(api_type == "responses")
            )
            if model_id2:
                logger.info(
                    "auto_router.model_resolved",
                    request_id=request_id,
                    resolved_model_id=model_id2,
                    resolution_method="benchmark_fallback",
                    category=category2,
                    mode=mode2,
                )
                return AutoRouteResult(
                    resolved_model_id=model_id2, classifier_usages=classifier_usages
                )

        failure_reason = failure_reason2 or "invalid_response"

    # ── Both failed → use configured default ─────────────────────────────────
    reason = failure_reason or "invalid_response"
    AUTO_ROUTER_FALLBACK.labels(reason=reason).inc()
    logger.warning(
        "auto_router.default_used",
        request_id=request_id,
        fallback_reason=reason,
        default_model_id=settings.auto_router_default_model_id,
    )
    # Pass empty valid_ids: the configured default may not be a benchmark model.
    return _use_default(reason, set(), request_id, classifier_usages=classifier_usages)


def _use_default(
    reason: str,
    valid_ids: set[str],
    request_id: str,
    *,
    classifier_usages: list[ClassifierUsage] | None = None,
) -> AutoRouteResult:
    """
    Return an AutoRouteResult using the configured default model.

    Raises AutoRouterMisconfiguredError (HTTP 500) when:
      - auto_router_default_model_id is empty / not configured
      - the default is not in the enabled registry (valid_ids is non-empty)

    When valid_ids is empty (degraded registry state) the membership check is
    skipped — downstream resolve_routing() will raise naturally if truly gone.
    """
    default = settings.auto_router_default_model_id.strip()

    if not default:
        logger.error(
            "auto_router.misconfigured",
            request_id=request_id,
            detail="auto_router_default_model_id is not set.",
        )
        raise AutoRouterMisconfiguredError(
            "Auto Router default model is not configured. "
            "Set AUTO_ROUTER_DEFAULT_MODEL_ID in the environment."
        )

    if valid_ids and default not in valid_ids:
        logger.error(
            "auto_router.misconfigured",
            request_id=request_id,
            detail=f"Default model '{default}' is not in the enabled model registry.",
        )
        raise AutoRouterMisconfiguredError(
            f"Auto Router default model '{default}' is not in the enabled model registry."
        )

    return AutoRouteResult(
        resolved_model_id=default,
        used_fallback=True,
        fallback_reason=reason,
        classifier_usages=classifier_usages or [],
    )
