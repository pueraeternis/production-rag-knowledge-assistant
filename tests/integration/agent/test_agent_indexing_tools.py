"""Integration tests for agent indexing tools."""

import json
from unittest.mock import MagicMock

from knowledge_assistant.agent.graph import run_turn
from knowledge_assistant.agent.state import AgentState
from knowledge_assistant.agent.tools import ToolRegistry
from knowledge_assistant.llm.messages import GenerationResult, ToolCall
from knowledge_assistant.llm.stub_client import StubLLMClient
from knowledge_assistant.mcp_server.exceptions import APPROVAL_REQUIRED


class TestAgentIndexingTools:
    def test_preview_tool_via_agent_turn(
        self,
        initial_state: AgentState,
        tool_registry: ToolRegistry,
        fake_indexing_pipeline: MagicMock,
    ) -> None:
        llm = StubLLMClient(
            responses=(
                GenerationResult(
                    content=None,
                    tool_calls=(
                        ToolCall(
                            id="call-preview",
                            name="index_documents_preview",
                            arguments=json.dumps(
                                {
                                    "sources": [
                                        {
                                            "kind": "file",
                                            "location": "docs/handbook.md",
                                        },
                                    ],
                                },
                            ),
                        ),
                    ),
                ),
                GenerationResult(content="Preview complete: 4 chunks.", tool_calls=()),
            ),
        )

        turn_result = run_turn(
            state=initial_state,
            user_message="Preview indexing docs/handbook.md",
            llm_client=llm,
            tool_registry=tool_registry,
        )

        fake_indexing_pipeline.preview_indexing.assert_called_once()
        assert turn_result.answer == "Preview complete: 4 chunks."

    def test_apply_without_approval_returns_tool_error(
        self,
        initial_state: AgentState,
        tool_registry: ToolRegistry,
        fake_indexing_pipeline: MagicMock,
    ) -> None:
        llm = StubLLMClient(
            responses=(
                GenerationResult(
                    content=None,
                    tool_calls=(
                        ToolCall(
                            id="call-apply",
                            name="index_documents_apply",
                            arguments=json.dumps(
                                {
                                    "sources": [
                                        {
                                            "kind": "file",
                                            "location": "docs/handbook.md",
                                        },
                                    ],
                                    "approval_confirmed": False,
                                },
                            ),
                        ),
                    ),
                ),
                GenerationResult(
                    content="Apply was rejected pending approval.",
                    tool_calls=(),
                ),
            ),
        )

        turn_result = run_turn(
            state=initial_state,
            user_message="Apply indexing now",
            llm_client=llm,
            tool_registry=tool_registry,
        )

        fake_indexing_pipeline.index_documents.assert_not_called()
        tool_payload = json.loads(
            next(
                message.content
                for message in turn_result.state.messages
                if message.tool_call_id == "call-apply"
            )
            or "{}",
        )
        assert tool_payload["error"] == APPROVAL_REQUIRED

    def test_apply_with_approval_calls_pipeline(
        self,
        initial_state: AgentState,
        tool_registry: ToolRegistry,
        fake_indexing_pipeline: MagicMock,
    ) -> None:
        llm = StubLLMClient(
            responses=(
                GenerationResult(
                    content=None,
                    tool_calls=(
                        ToolCall(
                            id="call-apply",
                            name="index_documents_apply",
                            arguments=json.dumps(
                                {
                                    "sources": [
                                        {
                                            "kind": "file",
                                            "location": "docs/handbook.md",
                                        },
                                    ],
                                    "approval_confirmed": True,
                                },
                            ),
                        ),
                    ),
                ),
                GenerationResult(
                    content="Indexing applied successfully.",
                    tool_calls=(),
                ),
            ),
        )

        run_turn(
            state=initial_state,
            user_message="Apply approved indexing",
            llm_client=llm,
            tool_registry=tool_registry,
        )

        fake_indexing_pipeline.index_documents.assert_called_once()
