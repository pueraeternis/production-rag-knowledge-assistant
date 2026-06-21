"""Unit tests for tool registry dispatch."""

import json

import pytest
from pydantic import BaseModel

from knowledge_assistant.agent.exceptions import DuplicateToolError, UnknownToolError
from knowledge_assistant.agent.tools import ToolRegistry
from knowledge_assistant.llm.messages import ChatRole, ToolCall, ToolDefinition


class _FakeArgs(BaseModel):
    value: str


class _FakeTool:
    def __init__(self, name: str, *, result: str = '{"ok": true}') -> None:
        self._name = name
        self._result = result

    @property
    def name(self) -> str:
        return self._name

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self._name,
            description="fake tool",
            parameters={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        )

    def execute(self, arguments: dict[str, object]) -> str:
        _FakeArgs.model_validate(arguments)
        return self._result


class TestToolRegistry:
    def test_register_duplicate_raises(self) -> None:
        registry = ToolRegistry()
        registry.register(_FakeTool("alpha"))

        with pytest.raises(DuplicateToolError):
            registry.register(_FakeTool("alpha"))

    def test_definitions_sorted_by_name(self) -> None:
        registry = ToolRegistry()
        registry.register(_FakeTool("search_documents"))
        registry.register(_FakeTool("alpha"))

        names = tuple(defn.name for defn in registry.definitions())
        assert names == ("alpha", "search_documents")

    def test_dispatch_unknown_tool_raises(self) -> None:
        registry = ToolRegistry()
        call = ToolCall(id="call-1", name="missing", arguments="{}")

        with pytest.raises(UnknownToolError):
            registry.dispatch(call)

    def test_dispatch_invalid_arguments_returns_tool_error(self) -> None:
        registry = ToolRegistry()
        registry.register(_FakeTool("alpha"))
        call = ToolCall(id="call-1", name="alpha", arguments="{}")

        message = registry.dispatch(call)

        assert message.role is ChatRole.TOOL
        assert message.tool_call_id == "call-1"
        payload = json.loads(message.content or "{}")
        assert payload["error"] == "validation_error"

    def test_dispatch_success_returns_tool_message(self) -> None:
        registry = ToolRegistry()
        registry.register(_FakeTool("alpha", result='{"hits": []}'))
        call = ToolCall(
            id="call-1",
            name="alpha",
            arguments='{"value": "test"}',
        )

        message = registry.dispatch(call)

        assert message.role is ChatRole.TOOL
        assert message.content == '{"hits": []}'
