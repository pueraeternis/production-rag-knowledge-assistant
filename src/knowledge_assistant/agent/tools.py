"""Agent tool registry and dispatch."""

from __future__ import annotations

import json
from typing import Protocol, cast

from pydantic import ValidationError

from knowledge_assistant.agent.exceptions import DuplicateToolError, UnknownToolError
from knowledge_assistant.llm.messages import (
    ChatMessage,
    ChatRole,
    ToolCall,
    ToolDefinition,
)
from knowledge_assistant.mcp_server.exceptions import (
    APPROVAL_REQUIRED,
    ApprovalRequiredError,
)

_INDEXING_SOURCE_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["file", "directory"]},
        "location": {"type": "string"},
        "recursive": {"type": "boolean"},
    },
    "required": ["kind", "location"],
}

SEARCH_DOCUMENTS_PARAMETERS: dict[str, object] = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "top_k": {"type": "integer", "minimum": 1},
    },
    "required": ["query"],
}

INDEX_DOCUMENTS_PREVIEW_PARAMETERS: dict[str, object] = {
    "type": "object",
    "properties": {
        "sources": {
            "type": "array",
            "items": _INDEXING_SOURCE_SCHEMA,
            "minItems": 1,
        },
    },
    "required": ["sources"],
}

INDEX_DOCUMENTS_APPLY_PARAMETERS: dict[str, object] = {
    "type": "object",
    "properties": {
        "sources": {
            "type": "array",
            "items": _INDEXING_SOURCE_SCHEMA,
            "minItems": 1,
        },
        "rebuild": {"type": "boolean"},
        "approval_confirmed": {"type": "boolean"},
    },
    "required": ["sources", "approval_confirmed"],
}


class AgentTool(Protocol):
    """Project-local tool abstraction for MCP handler adapters."""

    @property
    def name(self) -> str: ...

    def definition(self) -> ToolDefinition: ...

    def execute(self, arguments: dict[str, object]) -> str: ...


def tool_error_content(*, error: str, detail: str) -> str:
    return json.dumps({"error": error, "detail": detail})


class ToolRegistry:
    """Register agent tools and dispatch model-emitted tool calls."""

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        if tool.name in self._tools:
            raise DuplicateToolError(tool.name)
        self._tools[tool.name] = tool

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(
            self._tools[name].definition() for name in sorted(self._tools.keys())
        )

    def dispatch(self, call: ToolCall) -> ChatMessage:
        tool = self._tools.get(call.name)
        if tool is None:
            raise UnknownToolError(call.name)

        try:
            arguments = json.loads(call.arguments)
        except json.JSONDecodeError:
            content = tool_error_content(
                error="invalid_arguments",
                detail="tool arguments must be valid JSON",
            )
            return ChatMessage(
                role=ChatRole.TOOL,
                content=content,
                tool_call_id=call.id,
            )

        if not isinstance(arguments, dict):
            content = tool_error_content(
                error="invalid_arguments",
                detail="tool arguments must be a JSON object",
            )
            return ChatMessage(
                role=ChatRole.TOOL,
                content=content,
                tool_call_id=call.id,
            )

        try:
            result = tool.execute(cast("dict[str, object]", arguments))
        except ValidationError as exc:
            content = tool_error_content(
                error="validation_error",
                detail=str(exc),
            )
            return ChatMessage(
                role=ChatRole.TOOL,
                content=content,
                tool_call_id=call.id,
            )
        except ApprovalRequiredError as exc:
            content = tool_error_content(
                error=APPROVAL_REQUIRED,
                detail=exc.message,
            )
            return ChatMessage(
                role=ChatRole.TOOL,
                content=content,
                tool_call_id=call.id,
            )

        return ChatMessage(
            role=ChatRole.TOOL,
            content=result,
            tool_call_id=call.id,
        )
