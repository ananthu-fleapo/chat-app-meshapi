"""
Abstract base for all upstream AI provider adapters.

Each concrete adapter (OpenRouter, direct OpenAI, Anthropic, etc.) implements
this interface. The rest of the application only depends on this ABC, making
providers swappable without touching inference logic.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.schemas.chat import ChatCompletionRequest
from app.schemas.responses import ResponsesRequest
from app.schemas.embeddings import EmbeddingsRequest


class ProviderAdapter(ABC):
    async def embeddings(
        self,
        request: EmbeddingsRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        """
        Non-streaming embeddings request.

        Adapters that do not support embeddings may inherit this default and
        raise NotImplementedError until support is added.
        """
        raise NotImplementedError("Embeddings are not implemented for this provider.")

    @abstractmethod
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        """
        Non-streaming completion.
        Returns the upstream response as a parsed dict (forwarded as-is to client).
        Raises UpstreamError or GatewayTimeoutError on failure.
        api_key:           per-request auth override (owner's provisioned key).
        owner:             stable identifier forwarded as the `user` field for abuse detection.
        provider_model_id: exact upstream model ID from model_prices.provider_model_id.
                           If set, used directly; otherwise adapter falls back to its
                           internal _MODEL_MAP translation.
        """
        ...

    @abstractmethod
    async def stream_chat_completion(
        self,
        request: ChatCompletionRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """
        Streaming completion.
        Yields raw SSE byte chunks from the upstream provider.
        The caller is responsible for forwarding these to the client via StreamingResponse.
        Raises UpstreamError before yielding if the upstream returns a non-2xx status.
        api_key:           per-request auth override (owner's provisioned key).
        owner:             stable identifier forwarded as the `user` field for abuse detection.
        provider_model_id: exact upstream model ID (see chat_completion docstring).
        """
        ...
        yield b""  # make the type-checker treat this as an async generator

    async def responses_create(
        self,
        request: ResponsesRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> dict:
        """Non-streaming Responses API. Not supported by default; override in adapters that support it."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support the Responses API."
        )

    async def stream_responses_create(
        self,
        request: ResponsesRequest,
        *,
        api_key: str | None = None,
        owner: str | None = None,
        provider_model_id: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """Streaming Responses API. Not supported by default; override in adapters that support it."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support the Responses API."
        )
        yield b""  # make the type-checker treat this as an async generator

    # ── Batch / Files API (optional) ─────────────────────────────────────────
    # Adapters that support async batch processing should implement all 8
    # methods below. The default raises NotImplementedError, which the batch
    # router catches and converts to HTTP 501.

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        purpose: str,
        *,
        api_key: str | None = None,
    ) -> dict:
        """Upload a file (e.g. batch input JSONL). Not supported by default."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support the Batch Files API."
        )

    async def get_file(self, file_id: str, *, api_key: str | None = None) -> dict:
        """Get file metadata. Not supported by default."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support the Batch Files API."
        )

    async def delete_file(self, file_id: str, *, api_key: str | None = None) -> dict:
        """Delete a file. Not supported by default."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support the Batch Files API."
        )

    async def get_file_content(self, file_id: str, *, api_key: str | None = None) -> bytes:
        """Download raw file bytes. Not supported by default."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support the Batch Files API."
        )

    async def create_batch(
        self,
        input_file_id: str,
        endpoint: str,
        completion_window: str,
        metadata: dict | None = None,
        *,
        api_key: str | None = None,
    ) -> dict:
        """Create a batch job. Not supported by default."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support the Batch API."
        )

    async def get_batch(self, batch_id: str, *, api_key: str | None = None) -> dict:
        """Get batch status. Not supported by default."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support the Batch API."
        )

    async def list_batches(
        self,
        after: str | None = None,
        limit: int = 20,
        *,
        api_key: str | None = None,
    ) -> dict:
        """List batch jobs. Not supported by default."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support the Batch API."
        )

    async def cancel_batch(self, batch_id: str, *, api_key: str | None = None) -> dict:
        """Cancel a batch job. Not supported by default."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support the Batch API."
        )

    def parse_batch_results(self, content: bytes) -> list[dict]:
        """
        Parse provider-specific batch output bytes into a normalized list of
        per-request result dicts.

        Each dict must contain:
          success          bool   — True if the request completed without error
          model            str    — normalized model name matching model_prices
                                    (e.g. "openai/gpt-4o-mini")
          prompt_tokens    int
          completion_tokens int
          cached_tokens    int

        Adapters that support batch must implement this method.
        The batch router calls it to aggregate tokens and cost — it never
        parses provider-specific output formats directly.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement parse_batch_results()."
        )
