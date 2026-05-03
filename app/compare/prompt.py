"""
Comparison prompt builder.

Constructs the messages list sent to the comparison LLM after all fan-out
models have responded.  Isolated from the engine so it is unit-testable
without requiring async context or mock adapters.
"""

from __future__ import annotations

from app.schemas.chat import Message
from app.schemas.compare import ModelCompareResult

_DEFAULT_SYSTEM = (
    "You are an expert AI evaluator comparing responses from multiple AI models "
    "to the same prompt. Analyze the responses and provide a structured comparison "
    "covering: (1) accuracy and correctness, (2) completeness, (3) clarity and style, "
    "(4) unique strengths each model demonstrated, and (5) which response you recommend "
    "and why. Be concise and objective."
)


def build_comparison_messages(
    original_messages: list[Message],
    results: list[ModelCompareResult],
    custom_instructions: str | None = None,
) -> list[dict]:
    """
    Build the messages list for the comparison LLM.

    Only successful results (result.error is None) should be passed in;
    the caller is responsible for filtering.  If results contains error
    entries anyway, they are rendered as ERROR blocks so the comparison LLM
    is aware of the failure.

    Returns a plain list[dict] (not list[Message]) so callers can pass it
    directly to ChatCompletionRequest without a double-serialization round-trip.
    """
    system_content = custom_instructions or _DEFAULT_SYSTEM

    failed = [r for r in results if r.error is not None]

    # Reconstruct the original conversation as a readable block
    conv_lines: list[str] = []
    for msg in original_messages:
        role = msg.role.upper()
        if isinstance(msg.content, str):
            content = msg.content
        elif msg.content is None:
            content = "(no content)"
        else:
            # Multi-part content — extract text parts only
            text_parts = [p.text for p in msg.content if p.type == "text" and p.text]
            content = " ".join(text_parts) if text_parts else "[non-text content]"
        conv_lines.append(f"{role}: {content}")
    original_block = "\n".join(conv_lines)

    # Format each model response
    response_blocks: list[str] = []
    for i, result in enumerate(results, start=1):
        if result.error:
            block = f"## Response {i} — {result.model}\nERROR: {result.error}"
        else:
            content = result.content or "(empty response)"
            block = f"## Response {i} — {result.model}\n{content}"
        response_blocks.append(block)

    responses_text = "\n\n".join(response_blocks)

    # Add a note when some models failed
    partial_note = ""
    if failed:
        plural = "models" if len(failed) > 1 else "model"
        partial_note = (
            f"\n\nNote: {len(failed)} out of {len(results)} {plural} failed to respond "
            f"({', '.join(r.model for r in failed)}). Base your comparison only on the "
            "responses shown above."
        )

    return [
        {"role": "system", "content": system_content},
        {
            "role": "user",
            "content": (
                f"Original conversation:\n{original_block}\n\n"
                f"Model responses:\n\n{responses_text}"
                f"{partial_note}"
            ),
        },
        {
            "role": "user",
            "content": "Please provide your structured comparison and recommendation.",
        },
    ]
