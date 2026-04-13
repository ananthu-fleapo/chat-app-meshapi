"""
Request / response schemas for the embeddings endpoint.

The wire shape follows the OpenAI/OpenRouter embeddings API. We validate the
top-level request fields while forwarding the upstream response body as-is.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Provider preferences ──────────────────────────────────────────────────────

class ProviderPreferences(BaseModel):
    """OpenRouter provider routing preferences."""

    order: list[str] | None = Field(
        default=None,
        description="Preferred provider order, e.g. ['perplexity', 'openai'].",
    )
    allow_fallbacks: bool | None = Field(
        default=None,
        description="Whether to fall back to other providers if the first is unavailable.",
    )
    require_parameters: bool | None = Field(
        default=None,
        description="Only use providers that support all requested parameters.",
    )
    data_collection: Literal["allow", "deny"] | None = Field(
        default=None,
        description="Control whether the provider may use the request for training.",
    )


# ── Request ───────────────────────────────────────────────────────────────────

class EmbeddingsRequest(BaseModel):
    """
    Request body for `POST /v1/embeddings`.

    Mirrors the OpenAI / OpenRouter embeddings API. The `input` field accepts
    four shapes:

    - **string** — a single text to embed
    - **list[string]** — a batch of texts
    - **list[int]** — a single pre-tokenised input (token IDs)
    - **list[list[int]]** — a batch of pre-tokenised inputs
    """

    model: str | None = Field(
        default=None,
        description="Model ID to use for embedding, e.g. `perplexity/pplx-embed-v1-4b`.",
        examples=["perplexity/pplx-embed-v1-4b", "openai/text-embedding-3-small"],
    )
    input: (
        str
        | list[str]
        | list[int]
        | list[list[int]]
    ) = Field(
        description=(
            "Text(s) to embed. "
            "Accepts a string, list of strings, list of token IDs, "
            "or a list of token ID lists."
        ),
    )
    dimensions: int | None = Field(
        default=None,
        ge=1,
        description="Number of dimensions for the output embedding vector (model-dependent).",
    )
    encoding_format: Literal["float", "base64"] | None = Field(
        default=None,
        description="Format of the returned embedding. Defaults to `float`.",
    )
    input_type: str | None = Field(
        default=None,
        description=(
            "Intended use of the embedding, e.g. `query` or `document`. "
            "Some models use this to apply asymmetric embedding."
        ),
    )
    provider: str | ProviderPreferences | None = Field(
        default=None,
        description=(
            "Provider routing preferences. Pass a provider slug string (e.g. `'perplexity'`) "
            "or a `ProviderPreferences` object to control fallback and ordering behaviour."
        ),
    )
    user: str | None = Field(
        default=None,
        max_length=256,
        description="End-user identifier for abuse monitoring (forwarded to OpenRouter).",
    )

    @field_validator("input")
    @classmethod
    def input_must_not_be_empty(cls, v: object) -> object:
        if isinstance(v, list) and len(v) == 0:
            raise ValueError("input must not be an empty list")
        return v
