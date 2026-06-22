"""Unit tests for LangGraph routing."""

import json

import pytest

from knowledge_assistant.agent.config import AgentSettings
from knowledge_assistant.agent.graph import build_agent_graph, run_turn
from knowledge_assistant.agent.prompts import SYSTEM_PROMPT
from knowledge_assistant.agent.state import AgentState
from knowledge_assistant.agent.tools import ToolRegistry
from knowledge_assistant.llm.messages import (
    ChatMessage,
    ChatRole,
    GenerationResult,
    ToolCall,
    ToolDefinition,
)
from knowledge_assistant.llm.stub_client import StubLLMClient


class _RecordingTool:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[dict[str, object]] = []

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="records calls",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )

    def execute(self, arguments: dict[str, object]) -> str:
        self.calls.append(arguments)
        return json.dumps({"hits": [], "query": arguments.get("query")})


def _system_state() -> AgentState:
    return AgentState(
        messages=(ChatMessage(role=ChatRole.SYSTEM, content=SYSTEM_PROMPT),),
    )


class TestGraphRouting:
    def test_text_only_response_ends_after_agent_node(self) -> None:
        llm = StubLLMClient(
            responses=(GenerationResult(content="Hello without tools", tool_calls=()),),
        )
        graph = build_agent_graph(llm, ToolRegistry())

        output = graph.invoke(
            {
                "messages": (ChatMessage(role=ChatRole.USER, content="hi"),),
                "tool_iteration_count": 0,
                "final_response": None,
                "pending_tool_calls": (),
            },
        )

        assert output["final_response"] == "Hello without tools"
        assert output["pending_tool_calls"] == ()
        assert llm.call_count == 1

    def test_tool_call_then_final_answer_routes_through_tool_node(self) -> None:
        search_tool = _RecordingTool("search_documents")
        registry = ToolRegistry()
        registry.register(search_tool)
        llm = StubLLMClient(
            responses=(
                GenerationResult(
                    content=None,
                    tool_calls=(
                        ToolCall(
                            id="call-1",
                            name="search_documents",
                            arguments='{"query": "policy"}',
                        ),
                    ),
                ),
                GenerationResult(
                    content="Grounded answer about policy.",
                    tool_calls=(),
                ),
            ),
        )
        graph = build_agent_graph(llm, registry)

        output = graph.invoke(
            {
                "messages": (
                    ChatMessage(role=ChatRole.USER, content="What is the policy?"),
                ),
                "tool_iteration_count": 0,
                "final_response": None,
                "pending_tool_calls": (),
            },
        )

        assert search_tool.calls == [{"query": "policy"}]
        assert output["tool_iteration_count"] == 1
        assert output["final_response"] == "Grounded answer about policy."
        tool_messages = [
            message for message in output["messages"] if message.role is ChatRole.TOOL
        ]
        assert len(tool_messages) == 1
        assert llm.call_count == 2

    def test_max_tool_iterations_stops_with_refusal(self) -> None:
        search_tool = _RecordingTool("search_documents")
        registry = ToolRegistry()
        registry.register(search_tool)
        llm = StubLLMClient(
            responses=(
                GenerationResult(
                    content=None,
                    tool_calls=(
                        ToolCall(
                            id="call-1",
                            name="search_documents",
                            arguments='{"query": "one"}',
                        ),
                    ),
                ),
                GenerationResult(
                    content=None,
                    tool_calls=(
                        ToolCall(
                            id="call-2",
                            name="search_documents",
                            arguments='{"query": "two"}',
                        ),
                    ),
                ),
            ),
        )
        settings = AgentSettings(max_tool_iterations=1)
        graph = build_agent_graph(llm, registry, settings=settings)

        output = graph.invoke(
            {
                "messages": (
                    ChatMessage(role=ChatRole.USER, content="search repeatedly"),
                ),
                "tool_iteration_count": 0,
                "final_response": None,
                "pending_tool_calls": (),
            },
        )

        assert output["tool_iteration_count"] == 1
        assert output["final_response"] == (
            "Tool iteration limit reached. Unable to complete additional tool calls."
        )
        assert search_tool.calls == [{"query": "one"}]

    def test_unknown_tool_appends_error_tool_message(self) -> None:
        llm = StubLLMClient(
            responses=(
                GenerationResult(
                    content=None,
                    tool_calls=(
                        ToolCall(
                            id="call-1",
                            name="unknown_tool",
                            arguments="{}",
                        ),
                    ),
                ),
                GenerationResult(content="Continuing after tool error.", tool_calls=()),
            ),
        )
        graph = build_agent_graph(llm, ToolRegistry())

        output = graph.invoke(
            {
                "messages": (ChatMessage(role=ChatRole.USER, content="call bad tool"),),
                "tool_iteration_count": 0,
                "final_response": None,
                "pending_tool_calls": (),
            },
        )

        tool_messages = [
            message for message in output["messages"] if message.role is ChatRole.TOOL
        ]
        assert len(tool_messages) == 1
        payload = json.loads(tool_messages[0].content or "{}")
        assert payload["error"] == "unknown_tool"


class TestRunTurn:
    def test_run_turn_rejects_empty_user_message(self) -> None:
        with pytest.raises(ValueError, match="user_message"):
            run_turn(
                state=_system_state(),
                user_message="   ",
                llm_client=StubLLMClient(
                    responses=(GenerationResult(content="ok"),),
                ),
                tool_registry=ToolRegistry(),
            )

    def test_run_turn_appends_user_message_and_returns_final_response(self) -> None:
        llm = StubLLMClient(
            responses=(GenerationResult(content="Direct answer"),),
        )
        turn_result = run_turn(
            state=_system_state(),
            user_message="hello",
            llm_client=llm,
            tool_registry=ToolRegistry(),
        )

        assert turn_result.state.messages[1].role is ChatRole.USER
        assert turn_result.state.messages[1].content == "hello"
        assert turn_result.state.final_response == "Direct answer"
        assert turn_result.answer == "Direct answer"
