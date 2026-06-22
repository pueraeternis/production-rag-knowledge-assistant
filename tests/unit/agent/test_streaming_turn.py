"""Unit tests for streaming turn execution."""

import json

import pytest

from knowledge_assistant.agent.config import AgentSettings
from knowledge_assistant.agent.graph import build_agent_graph, run_turn_streaming
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
from knowledge_assistant.llm.streaming_stub_client import StreamingStubLLMClient
from knowledge_assistant.llm.stub_client import StubLLMClient


class _RecordingTool:
    def __init__(self, name: str) -> None:
        self.name = name

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
        return json.dumps({"hits": [], "query": arguments.get("query")})


def _system_state() -> AgentState:
    return AgentState(
        messages=(ChatMessage(role=ChatRole.SYSTEM, content=SYSTEM_PROMPT),),
    )


class TestStreamingTurn:
    def test_run_turn_streaming_rejects_non_streaming_client(self) -> None:
        llm = StubLLMClient(responses=(GenerationResult(content="ok"),))
        with pytest.raises(TypeError, match="StreamingLLMClient"):
            run_turn_streaming(
                state=_system_state(),
                user_message="hello",
                llm_client=llm,
                tool_registry=ToolRegistry(),
            )

    def test_streaming_turn_uses_chat_for_tools_and_stream_for_final_answer(
        self,
    ) -> None:
        registry = ToolRegistry()
        registry.register(_RecordingTool("search_documents"))
        llm = StreamingStubLLMClient(
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
                GenerationResult(content=None, tool_calls=()),
            ),
            stream_deltas=("Grounded ", "answer."),
        )
        turn_stream = run_turn_streaming(
            state=_system_state(),
            user_message="What is the policy?",
            llm_client=llm,
            tool_registry=registry,
        )
        chunks = [chunk.content_delta for chunk in turn_stream]
        turn_result = turn_stream.result()

        assert chunks == ["Grounded ", "answer."]
        assert turn_result.answer == "Grounded answer."
        assert llm.call_count == 2
        assert llm.stream_call_count == 1

    def test_graph_topology_unchanged(self) -> None:
        llm = StubLLMClient(responses=(GenerationResult(content="ok"),))
        graph = build_agent_graph(llm, ToolRegistry(), settings=AgentSettings())
        node_names = set(graph.get_graph().nodes.keys())
        assert node_names == {
            "__start__",
            "__end__",
            "agent_node",
            "tool_node",
            "max_iterations",
        }
