"""
Vertex AI image generation handler (Imagen models).

Calls the Vertex AI predict endpoint:
  POST https://{location}-aiplatform.googleapis.com/v1/projects/{project}/
       locations/{location}/publishers/google/models/{model}:predict

Vertex always returns base64-encoded images (bytesBase64Encoded + mimeType),
so the response_format field in ImageOptions is ignored — callers always
receive ImageGeneratedItem(url=None, b64_json=..., mime_type=...).
"""

from __future__ import annotations

import structlog

from app.exceptions import UpstreamError
from app.providers.response_formatter import ImageGeneratedItem
from app.schemas.chat import ImageOptions

logger = structlog.get_logger()

# Maps "WxH" size strings to Vertex aspectRatio strings.
_ASPECT_RATIO: dict[str, str] = {
    "1024x1024": "1:1",
    "1024x1792": "9:16",
    "1792x1024": "16:9",
    "896x1152": "3:4",
    "1152x896": "4:3",
}


def _size_to_aspect(size: str) -> str:
    return _ASPECT_RATIO.get(size, "1:1")


async def generate(
    prompt: str,
    *,
    provider_model_id: str,
    opts: ImageOptions,
    api_key: str | None,  # unused — Vertex uses service-account token
) -> list[ImageGeneratedItem]:
    """
    Call the Vertex Imagen :predict endpoint and return normalised results.

    Raises UpstreamError on non-2xx responses.
    """
    from app.providers.vertex_ai import VertexAIAdapter

    adapter = VertexAIAdapter.get()
    log = logger.bind(provider_model_id=provider_model_id, n=opts.n)

    url = (
        f"https://{adapter._location}-aiplatform.googleapis.com/v1"
        f"/projects/{adapter._project_id}"
        f"/locations/{adapter._location}"
        f"/publishers/google/models/{provider_model_id}:predict"
    )
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": opts.n,
            "aspectRatio": _size_to_aspect(opts.size),
        },
    }

    auth_headers = await adapter._auth_headers()
    log.debug("vertex_image_generate_request", url=url, aspect=_size_to_aspect(opts.size))

    response = await adapter._google_client.post(url, json=payload, headers=auth_headers)

    if response.status_code >= 400:
        raw = response.text[:500]
        level = "error" if response.status_code >= 500 else "warning"
        log.msg(
            "vertex_image_http_error",
            _level=level,
            status=response.status_code,
            body=raw,
        )
        raise UpstreamError(f"Vertex image generation failed ({response.status_code}): {raw}")

    predictions: list[dict] = response.json().get("predictions", [])
    log.info("vertex_image_generate_ok", count=len(predictions))

    return [
        ImageGeneratedItem(
            url=None,
            b64_json=pred.get("bytesBase64Encoded"),
            mime_type=pred.get("mimeType", "image/png"),
        )
        for pred in predictions
    ]
