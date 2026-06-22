"""Unit tests for shared tool-loop execution."""

import json
from typing import cast

from knowledge_assistant.agent.config import AgentSettings
from knowledge_assistant.agent.prompts import SYSTEM_PROMPT
from knowledge_assistant.agent.state import AgentState
from knowledge_assistant.agent.streaming import run_tool_loop
from knowledge_assistant.agent.tools import ToolRegistry
from knowledge_assistant.llm.config import GenerationSettings, LlmSettings
from knowledge_assistant.llm.messages import (
    ChatMessage,
    ChatRole,
    GenerationResult,
    ToolCall,
)
from knowledge_assistant.llm.openai_client import build_chat_request_body
from knowledge_assistant.llm.stub_client import StubLLMClient


class _RecordingTool:
    def __init__(self, name: str) -> None:
        self.name = name
        self.call_count = 0

    def definition(self):
        from knowledge_assistant.llm.messages import ToolDefinition

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
        self.call_count += 1
        return json.dumps({"hits": [], "query": arguments.get("query")})


def _system_state() -> AgentState:
    return AgentState(
        messages=(ChatMessage(role=ChatRole.SYSTEM, content=SYSTEM_PROMPT),),
    )


class TestRunToolLoop:
    def test_assistant_tool_calls_are_preserved_for_follow_up_requests(self) -> None:
        registry = ToolRegistry()
        registry.register(_RecordingTool("search_documents"))
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
                GenerationResult(content=None, tool_calls=()),
            ),
        )
        input_state = AgentState(
            messages=(
                *_system_state().messages,
                ChatMessage(role=ChatRole.USER, content="What is the policy?"),
            ),
            tool_iteration_count=0,
            final_response=None,
            pending_tool_calls=(),
        )

        post_tool_state, _sources, outcome = run_tool_loop(
            state=input_state,
            llm_client=llm,
            tool_registry=registry,
            settings=AgentSettings(),
            generation_settings=GenerationSettings(),
        )

        assert outcome == "stream_final"
        assert llm.call_count == 2
        assistant_messages = [
            message
            for message in post_tool_state.messages
            if message.role is ChatRole.ASSISTANT
        ]
        assert len(assistant_messages) == 1
        assert assistant_messages[0].tool_calls[0].name == "search_documents"

        body = build_chat_request_body(
            post_tool_state.messages,
            llm_settings=LlmSettings(
                base_url="http://localhost/v1",
                api_key="test",
                default_model="test",
            ),
            tools=registry.definitions(),
        )
        messages = cast("list[dict[str, object]]", body["messages"])
        serialized_assistant = next(
            message for message in messages if message["role"] == "assistant"
        )
        tool_calls = cast("list[dict[str, object]]", serialized_assistant["tool_calls"])
        function = cast("dict[str, object]", tool_calls[0]["function"])
        assert function["name"] == "search_documents"

    def test_skipped_search_produces_no_sources(self) -> None:
        registry = ToolRegistry()
        search_tool = _RecordingTool("search_documents")
        registry.register(search_tool)
        llm = StubLLMClient(
            responses=(GenerationResult(content=None, tool_calls=()),),
        )
        input_state = AgentState(
            messages=(
                *_system_state().messages,
                ChatMessage(
                    role=ChatRole.USER,
                    content="What is the capital of France?",
                ),
            ),
            tool_iteration_count=0,
            final_response=None,
            pending_tool_calls=(),
        )

        _post_tool_state, sources, outcome = run_tool_loop(
            state=input_state,
            llm_client=llm,
            tool_registry=registry,
            settings=AgentSettings(),
            generation_settings=GenerationSettings(),
        )

        assert outcome == "stream_final"
        assert search_tool.call_count == 0
        assert sources == ()
        assert llm.call_count == 1
