"""Deterministic streaming LLM client for tests."""

from __future__ import annotations

from collections.abc import Iterator

from knowledge_assistant.llm.config import GenerationSettings
from knowledge_assistant.llm.messages import (
    ChatMessage,
    GenerationResult,
    StreamChunk,
    ToolDefinition,
)
from knowledge_assistant.llm.stub_client import StubLLMClient


class StreamingStubLLMClient(StubLLMClient):
    """Scripted ``chat`` responses plus deterministic ``stream_chat`` deltas."""

    def __init__(
        self,
        responses: tuple[GenerationResult, ...],
        *,
        stream_deltas: tuple[str, ...] = (),
    ) -> None:
        super().__init__(responses)
        self._stream_deltas = stream_deltas
        self._stream_call_index = 0

    @property
    def stream_call_count(self) -> int:
        """Number of completed ``stream_chat`` invocations."""
        return self._stream_call_index

    def stream_chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> Iterator[StreamChunk]:
        _ = messages
        _ = settings
        _ = tools
        self._stream_call_index += 1
        for delta in self._stream_deltas:
            yield StreamChunk(content_delta=delta)
