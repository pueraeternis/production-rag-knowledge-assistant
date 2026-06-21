"""Unit tests for agent state."""

import pytest

from knowledge_assistant.agent.state import (
    AgentState,
    append_messages,
    graph_output_to_state,
    state_to_graph_input,
)
from knowledge_assistant.llm.messages import ChatMessage, ChatRole


class TestAgentState:
    def test_rejects_negative_tool_iteration_count(self) -> None:
        with pytest.raises(ValueError, match="tool_iteration_count"):
            AgentState(tool_iteration_count=-1)

    def test_append_messages_returns_new_state(self) -> None:
        initial = AgentState()
        user = ChatMessage(role=ChatRole.USER, content="hello")
        updated = append_messages(initial, (user,))

        assert initial.messages == ()
        assert updated.messages == (user,)

    def test_graph_round_trip_preserves_fields(self) -> None:
        user = ChatMessage(role=ChatRole.USER, content="question")
        state = AgentState(
            messages=(user,),
            tool_iteration_count=2,
            final_response="answer",
        )

        graph_input = state_to_graph_input(state)
        restored = graph_output_to_state(graph_input)

        assert restored == state
