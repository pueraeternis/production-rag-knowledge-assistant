"""Integration tests for agent search flow."""

import json
from unittest.mock import MagicMock

from knowledge_assistant.agent.graph import run_turn
from knowledge_assistant.agent.state import AgentState
from knowledge_assistant.agent.tools import ToolRegistry
from knowledge_assistant.llm.messages import (
    ChatRole,
    GenerationResult,
    ToolCall,
)
from knowledge_assistant.llm.stub_client import StubLLMClient


class TestAgentSearchFlow:
    def test_search_tool_flow_populates_tool_message_with_sources(
        self,
        initial_state: AgentState,
        tool_registry: ToolRegistry,
        fake_retriever: MagicMock,
    ) -> None:
        llm = StubLLMClient(
            responses=(
                GenerationResult(
                    content=None,
                    tool_calls=(
                        ToolCall(
                            id="call-search",
                            name="search_documents",
                            arguments='{"query": "remote work policy"}',
                        ),
                    ),
                ),
                GenerationResult(
                    content=(
                        "Remote work is allowed two days per week "
                        "(Employee Handbook, docs/handbook.md)."
                    ),
                    tool_calls=(),
                ),
            ),
        )

        result = run_turn(
            state=initial_state,
            user_message="What is the remote work policy?",
            llm_client=llm,
            tool_registry=tool_registry,
        )

        fake_retriever.retrieve.assert_called_once()
        tool_messages = [
            message for message in result.messages if message.role is ChatRole.TOOL
        ]
        assert len(tool_messages) == 1
        payload = json.loads(tool_messages[0].content or "{}")
        assert payload["hits"][0]["source"]["document_title"] == "Employee Handbook"
        assert payload["hits"][0]["source"]["document_path"] == "docs/handbook.md"
        assert result.final_response is not None
        assert "remote work" in result.final_response.lower()

    def test_conversational_turn_without_tools(
        self,
        initial_state: AgentState,
        tool_registry: ToolRegistry,
    ) -> None:
        llm = StubLLMClient(
            responses=(GenerationResult(content="Hello! How can I help?"),),
        )

        result = run_turn(
            state=initial_state,
            user_message="Hi there",
            llm_client=llm,
            tool_registry=tool_registry,
        )

        assert result.final_response == "Hello! How can I help?"
        assert not any(message.role is ChatRole.TOOL for message in result.messages)
