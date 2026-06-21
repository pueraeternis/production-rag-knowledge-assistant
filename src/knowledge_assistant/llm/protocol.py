"""LLM client protocol."""

from __future__ import annotations

from typing import Protocol

from knowledge_assistant.llm.config import GenerationSettings
from knowledge_assistant.llm.messages import (
    ChatMessage,
    GenerationResult,
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
