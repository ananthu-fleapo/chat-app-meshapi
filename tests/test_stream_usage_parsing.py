"""
Unit tests for _scan_sse_buf — the SSE frame scanner that extracts token usage
from streaming OpenRouter responses.

Regression: usage was silently dropped when it arrived alongside a non-empty
choices array (e.g. Claude models bundle usage with the final content chunk).
The old guard `not obj.get("choices")` caused the miss; these tests pin that
behaviour so it can never regress.
"""

from __future__ import annotations

import json

import pytest


def _frame(obj: dict) -> bytes:
    """Encode a dict as a single SSE data frame."""
    return b"data: " + json.dumps(obj).encode() + b"\n\n"


def _done() -> bytes:
    return b"data: [DONE]\n\n"


def _content_chunk(content: str = "hi", usage=None) -> bytes:
    return _frame({
        "choices": [{"delta": {"content": content}, "finish_reason": None}],
        "usage": usage,
    })


def _usage_chunk_empty_choices(prompt: int, completion: int) -> bytes:
    """Standard OpenRouter usage chunk — choices=[], usage populated."""
    return _frame({
        "choices": [],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion},
    })


def _usage_chunk_with_choices(prompt: int, completion: int) -> bytes:
    """Claude-via-OpenRouter style — usage bundled with finish_reason in choices."""
    return _frame({
        "choices": [{"delta": {}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion},
    })


# ─────────────────────────────────────────────────────────────────────────────

class TestScanSseBuf:

    def _scan(self, buf: bytes, current: dict | None = None):
        from app.routers.inference import _scan_sse_buf
        return _scan_sse_buf(buf, current)

    # ── basic extraction ─────────────────────────────────────────────────────

    def test_extracts_usage_from_empty_choices_chunk(self):
        """Standard OpenRouter pattern: usage chunk has choices=[]."""
        buf = _usage_chunk_empty_choices(100, 50)
        usage, remaining = self._scan(buf)
        assert usage == {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        assert remaining == b""

    def test_extracts_usage_when_bundled_with_nonempty_choices(self):
        """
        Regression: Claude models via OpenRouter send usage alongside
        finish_reason in choices. The old `not obj.get("choices")` guard
        silently dropped this — now it must be captured.
        """
        buf = _usage_chunk_with_choices(200, 80)
        usage, remaining = self._scan(buf)
        assert usage is not None
        assert usage["prompt_tokens"] == 200
        assert usage["completion_tokens"] == 80

    def test_null_usage_in_regular_chunks_does_not_overwrite(self):
        """Regular content chunks carry "usage": null — must not clobber existing usage."""
        seed = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        buf = _content_chunk("hello", usage=None)
        usage, _ = self._scan(buf, seed)
        assert usage == seed

    def test_null_usage_in_first_chunk_stays_none(self):
        """No usage yet + regular chunk with usage:null → still None."""
        buf = _content_chunk("hello", usage=None)
        usage, _ = self._scan(buf)
        assert usage is None

    # ── multi-frame streams ──────────────────────────────────────────────────

    def test_usage_in_last_frame_after_content_chunks(self):
        """Full realistic stream: content chunks then usage chunk then [DONE]."""
        buf = (
            _content_chunk("Hello")
            + _content_chunk(" world")
            + _usage_chunk_empty_choices(120, 60)
            + _done()
        )
        usage, remaining = self._scan(buf)
        assert usage["prompt_tokens"] == 120
        assert usage["completion_tokens"] == 60
        assert remaining == b""

    def test_done_frame_is_skipped_without_error(self):
        buf = _done()
        usage, remaining = self._scan(buf)
        assert usage is None
        assert remaining == b""

    def test_later_usage_chunk_wins_over_earlier(self):
        """If somehow two usage chunks arrive, the last one wins."""
        buf = _usage_chunk_empty_choices(10, 5) + _usage_chunk_empty_choices(20, 10)
        usage, _ = self._scan(buf)
        assert usage["prompt_tokens"] == 20

    # ── partial frames / buffering ───────────────────────────────────────────

    def test_incomplete_frame_stays_in_remaining(self):
        """Data that doesn't end with \\n\\n is left in the buffer unprocessed."""
        incomplete = b"data: {partial"
        usage, remaining = self._scan(incomplete)
        assert usage is None
        assert remaining == incomplete

    def test_complete_frame_followed_by_partial(self):
        """Complete frame is processed; trailing partial is returned for next iteration."""
        complete = _usage_chunk_empty_choices(30, 15)
        partial = b"data: {incomplete"
        buf = complete + partial
        usage, remaining = self._scan(buf)
        assert usage["prompt_tokens"] == 30
        assert remaining == partial

    def test_empty_buf_returns_none_and_empty(self):
        usage, remaining = self._scan(b"")
        assert usage is None
        assert remaining == b""

    # ── robustness ───────────────────────────────────────────────────────────

    def test_malformed_json_does_not_raise(self):
        buf = b"data: {not valid json}\n\n"
        usage, remaining = self._scan(buf)
        assert usage is None

    def test_non_data_lines_are_ignored(self):
        buf = b"event: ping\ndata: {}\n\n"
        usage, remaining = self._scan(buf)
        assert usage is None

    def test_preserves_all_usage_fields(self):
        """cached_tokens and cost fields pass through unchanged."""
        chunk = _frame({
            "choices": [],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 25,
                "total_tokens": 75,
                "prompt_tokens_details": {"cached_tokens": 10},
                "cost": 0.000123,
            },
        })
        usage, _ = self._scan(chunk)
        assert usage["prompt_tokens_details"]["cached_tokens"] == 10
        assert usage["cost"] == pytest.approx(0.000123)
