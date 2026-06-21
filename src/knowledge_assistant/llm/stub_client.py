"""Deterministic LLM client for tests."""

from __future__ import annotations

from knowledge_assistant.llm.config import GenerationSettings
from knowledge_assistant.llm.messages import (
    ChatMessage,
    GenerationResult,
    ToolDefinition,
)


class StubLLMClient:
    """Return scripted ``GenerationResult`` values in call order without network."""

    def __init__(
        self,
        responses: tuple[GenerationResult, ...],
    ) -> None:
        if not responses:
            msg = "StubLLMClient.responses must contain at least one GenerationResult"
            raise ValueError(msg)
        self._responses = responses
        self._call_index = 0

    def chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> GenerationResult:
        _ = messages
        _ = settings
        _ = tools
        if self._call_index >= len(self._responses):
            msg = (
                f"StubLLMClient exhausted scripted responses after "
                f"{len(self._responses)} call(s)"
            )
            raise IndexError(msg)
        result = self._responses[self._call_index]
        self._call_index += 1
        return result
