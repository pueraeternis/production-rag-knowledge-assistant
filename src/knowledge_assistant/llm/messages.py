"""Chat-oriented transport DTOs for the LLM boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum


class ChatRole(StrEnum):
    """OpenAI-compatible chat message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """One message in a chat completion request."""

    role: ChatRole
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None

    def __post_init__(self) -> None:
        if self.role is ChatRole.TOOL and not self.tool_call_id:
            msg = "tool_call_id is required when role is TOOL"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """OpenAI-compatible tool definition for chat completions."""

    name: str
    description: str
    parameters: dict[str, object]

    def __post_init__(self) -> None:
        if not self.name.strip():
            msg = "ToolDefinition.name must be non-empty"
            raise ValueError(msg)
        if not self.description.strip():
            msg = "ToolDefinition.description must be non-empty"
            raise ValueError(msg)
        if self.parameters.get("type") != "object":
            msg = (
                "ToolDefinition.parameters must be a JSON Schema object "
                "with type 'object'"
            )
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Model-emitted tool call from a chat completion response."""

    id: str
    name: str
    arguments: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            msg = "ToolCall.id must be non-empty"
            raise ValueError(msg)
        if not self.name.strip():
            msg = "ToolCall.name must be non-empty"
            raise ValueError(msg)
        try:
            parsed = json.loads(self.arguments)
        except json.JSONDecodeError as exc:
            msg = "ToolCall.arguments must be valid JSON"
            raise ValueError(msg) from exc
        if not isinstance(parsed, dict):
            msg = "ToolCall.arguments must be a JSON object string"
            raise TypeError(msg)


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token usage statistics from a chat completion response."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0:
            msg = "prompt_tokens must be >= 0"
            raise ValueError(msg)
        if self.completion_tokens < 0:
            msg = "completion_tokens must be >= 0"
            raise ValueError(msg)
        if self.total_tokens < 0:
            msg = "total_tokens must be >= 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class StreamChunk:
    """One incremental model text delta from a streaming completion."""

    content_delta: str


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Result of one chat completion call."""

    content: str | None
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str | None = None
    model: str | None = None
    usage: TokenUsage | None = None
