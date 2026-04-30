"""
Image response formatter.

Converts provider-specific image generation results into the Chat Completions
response shape so callers receive a consistent envelope regardless of provider.

All providers normalise their output to list[ImageGeneratedItem] before calling
format_image_as_chat_completion().  The formatter then builds an image_url
content part from whichever of url / b64_json is present, preferring b64_json
(which is always set for Vertex) over url.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class ImageGeneratedItem:
    url: str | None
    b64_json: str | None
    mime_type: str | None = field(default="image/png")


@dataclass
class ImageGenerationResult:
    """
    Normalised result returned by every image handler.

    items        — one entry per generated image.
    input_tokens — prompt tokens reported by the provider (None if unavailable).
    output_tokens— image/output tokens reported by the provider (None if unavailable).
    total_tokens — sum reported by the provider (None if unavailable).
    """

    items: list[ImageGeneratedItem]
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


def format_image_as_chat_completion(
    result: ImageGenerationResult,
    *,
    model_id: str,
    cost_usd: float | None = None,
) -> dict:
    """
    Build a Chat Completions response dict from an ImageGenerationResult.

    Each image becomes one choice; multi-image requests (n > 1) produce
    multiple choices with sequential index values.
    """
    choices = []
    for i, item in enumerate(result.items):
        if item.b64_json:
            mime = item.mime_type or "image/png"
            image_url = f"data:{mime};base64,{item.b64_json}"
        else:
            image_url = item.url or ""
        choices.append(
            {
                "index": i,
                "message": {
                    "role": "assistant",
                    "content": [{"type": "image_url", "image_url": {"url": image_url}}],
                },
                "finish_reason": "stop",
            }
        )
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_id,
        "choices": choices,
        "usage": {
            "prompt_tokens": result.input_tokens or 0,
            "completion_tokens": result.output_tokens or 0,
            "total_tokens": result.total_tokens or 0,
            "images_generated": len(result.items),
            "cost_usd": cost_usd,
        },
    }
