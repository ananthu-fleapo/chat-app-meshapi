from typing import Any
import structlog

logger = structlog.get_logger()

def _normalize_coupon_code(code: str | None) -> str | None:
    if code is None:
        return None
    normalized = code.strip().upper()
    return normalized or None

def _normalize_user_ids(user_ids: list[str] | None) -> list[str]:
    if not user_ids:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for user_id in user_ids:
        cleaned = user_id.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized
