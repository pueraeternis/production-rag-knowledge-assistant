"""LLM client protocol."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from knowledge_assistant.llm.config import GenerationSettings
from knowledge_assistant.llm.messages import (
    ChatMessage,
    GenerationResult,
    StreamChunk,
    ToolDefinition,
)


class LLMClient(Protocol):
    """Chat-oriented model invocation boundary."""

    def chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> GenerationResult:
        """Send a chat completion request and return the model response."""
        ...


@runtime_checkable
class StreamingLLMClient(LLMClient, Protocol):
    """Optional streaming capability extending the Plan 11 chat contract."""

    def stream_chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> Iterator[StreamChunk]:
        """Stream incremental text deltas from a chat completion request."""
        ...
