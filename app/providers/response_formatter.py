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


def format_image_as_chat_completion(
    items: list[ImageGeneratedItem],
    *,
    model_id: str,
) -> dict:
    """
    Build a Chat Completions response dict from a list of generated images.

    Each image becomes one choice; multi-image requests (n > 1) produce
    multiple choices with sequential index values.
    """
    choices = []
    for i, item in enumerate(items):
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
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
