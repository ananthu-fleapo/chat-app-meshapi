"""
Shared SSE parsing utilities used by inference and compare streaming paths.
"""

from __future__ import annotations

import json


def parse_sse_frame(frame: bytes) -> dict | None:
    """
    Parse one complete SSE frame (without trailing \\n\\n) into a structured dict.

    Returns None for [DONE], empty/unparseable frames, or frames with no useful content.
    Returns {"delta": str | None, "finish_reason": str | None, "usage": dict | None}
    where at least one value is non-None.
    """
    for line in frame.split(b"\n"):
        if not line.startswith(b"data: "):
            continue
        payload = line[6:].strip()
        if payload == b"[DONE]":
            return None
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            return None

        choices = obj.get("choices") or []
        delta_content: str | None = None
        finish_reason: str | None = None
        if choices:
            delta = choices[0].get("delta") or {}
            delta_content = delta.get("content")
            finish_reason = choices[0].get("finish_reason")

        usage = obj.get("usage") or None

        if delta_content is None and finish_reason is None and usage is None:
            return None

        return {"delta": delta_content, "finish_reason": finish_reason, "usage": usage}
    return None


def scan_sse_buf(buf: bytes, current_usage: dict | None) -> tuple[dict | None, bytes]:
    """
    Process all complete SSE frames (\\n\\n-delimited) in buf.

    Returns (updated_usage, remaining_buf).  Regular streaming chunks carry
    "usage": null which is falsy, so only a real usage object updates the
    return value.  The caller should not filter on choices — some providers
    (e.g. Claude via OpenRouter) bundle usage with a non-empty choices array
    in the final content chunk.
    """
    while b"\n\n" in buf:
        frame, buf = buf.split(b"\n\n", 1)
        for line in frame.split(b"\n"):
            if not line.startswith(b"data: "):
                continue
            payload = line[6:].strip()
            if payload == b"[DONE]":
                continue
            try:
                obj = json.loads(payload)
                if obj.get("usage"):
                    current_usage = obj["usage"]
            except (json.JSONDecodeError, KeyError):
                pass
    return current_usage, buf
