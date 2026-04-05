"""
Abstract base for all upstream AI provider adapters.

Each concrete adapter (OpenRouter, direct OpenAI, Anthropic, etc.) implements
this interface. The rest of the application only depends on this ABC, making
providers swappable without touching inference logic.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.schemas.chat import ChatCompletionRequest


class ProviderAdapter(ABC):
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
