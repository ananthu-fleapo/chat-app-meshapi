"""
Unit tests for app/compare/prompt.py — build_comparison_messages().
"""

from __future__ import annotations

import pytest

from app.compare.prompt import build_comparison_messages, _DEFAULT_SYSTEM
from app.schemas.chat import Message
from app.schemas.compare import ModelCompareResult, TokenUsage


def _result(model: str, content: str | None = "some content", error: str | None = None) -> ModelCompareResult:
    return ModelCompareResult(
        model=model,
        response_body=None,
        content=content,
        latency_ms=100,
        error=error,
        error_code="upstream_error" if error else None,
        usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        request_id=f"req::{model}",
    )


@pytest.fixture
def messages():
    return [
        Message(role="user", content="Explain recursion."),
    ]


def test_all_success_structure(messages):
    results = [_result("model-a"), _result("model-b")]
    msgs = build_comparison_messages(messages, results)

    assert len(msgs) == 3
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "user"


def test_default_system_content(messages):
    results = [_result("model-a"), _result("model-b")]
    msgs = build_comparison_messages(messages, results)
    assert msgs[0]["content"] == _DEFAULT_SYSTEM


def test_custom_instructions_replace_default(messages):
    custom = "Compare only on brevity."
    results = [_result("model-a"), _result("model-b")]
    msgs = build_comparison_messages(messages, results, custom_instructions=custom)
    assert msgs[0]["content"] == custom


def test_model_names_appear_in_response_blocks(messages):
    results = [_result("gpt-4o"), _result("claude-3")]
    msgs = build_comparison_messages(messages, results)
    body = msgs[1]["content"]
    assert "gpt-4o" in body
    assert "claude-3" in body


def test_response_content_appears(messages):
    results = [_result("m1", content="answer one"), _result("m2", content="answer two")]
    msgs = build_comparison_messages(messages, results)
    body = msgs[1]["content"]
    assert "answer one" in body
    assert "answer two" in body


def test_error_result_shows_error_prefix(messages):
    results = [_result("good-model"), _result("bad-model", content=None, error="timeout")]
    msgs = build_comparison_messages(messages, results)
    body = msgs[1]["content"]
    assert "ERROR: timeout" in body


def test_partial_failure_note_included(messages):
    results = [_result("good-model"), _result("bad-model", content=None, error="timeout")]
    msgs = build_comparison_messages(messages, results)
    body = msgs[1]["content"]
    assert "1 out of 2" in body
    assert "bad-model" in body


def test_no_partial_note_when_all_succeed(messages):
    results = [_result("a"), _result("b")]
    msgs = build_comparison_messages(messages, results)
    body = msgs[1]["content"]
    assert "out of" not in body


def test_original_message_appears(messages):
    results = [_result("a"), _result("b")]
    msgs = build_comparison_messages(messages, results)
    body = msgs[1]["content"]
    assert "Explain recursion" in body


def test_multipart_content_extracted(messages):
    from app.schemas.chat import ContentPart
    multi_msg = Message(
        role="user",
        content=[
            ContentPart(type="text", text="Hello"),
            ContentPart(type="image_url", image_url=None),
        ],
    )
    results = [_result("a")]
    msgs = build_comparison_messages([multi_msg], results)
    body = msgs[1]["content"]
    assert "Hello" in body


def test_empty_content_shows_placeholder(messages):
    results = [_result("m", content=None)]
    msgs = build_comparison_messages(messages, results)
    body = msgs[1]["content"]
    assert "(empty response)" in body


def test_final_user_message_asks_for_comparison(messages):
    results = [_result("a"), _result("b")]
    msgs = build_comparison_messages(messages, results)
    assert "comparison" in msgs[2]["content"].lower()
