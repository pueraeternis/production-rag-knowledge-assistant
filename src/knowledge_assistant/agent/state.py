"""LangGraph agent state and reducers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Annotated, TypedDict

from knowledge_assistant.llm.messages import ChatMessage, ToolCall


def _append_messages(
    left: tuple[ChatMessage, ...],
    right: tuple[ChatMessage, ...],
) -> tuple[ChatMessage, ...]:
    return left + right


def _replace_pending_tool_calls(
    _left: tuple[ToolCall, ...],
    right: tuple[ToolCall, ...],
) -> tuple[ToolCall, ...]:
    return right


class GraphState(TypedDict):
    """LangGraph state schema with reducers."""

    messages: Annotated[tuple[ChatMessage, ...], _append_messages]
    tool_iteration_count: int
    final_response: str | None
    pending_tool_calls: Annotated[tuple[ToolCall, ...], _replace_pending_tool_calls]


@dataclass(frozen=True, slots=True)
class AgentState:
    """In-memory conversation state for one agent session."""

    messages: tuple[ChatMessage, ...] = ()
    tool_iteration_count: int = 0
    final_response: str | None = None
    pending_tool_calls: tuple[ToolCall, ...] = ()

    def __post_init__(self) -> None:
        if self.tool_iteration_count < 0:
            msg = "tool_iteration_count must be >= 0"
            raise ValueError(msg)


def append_messages(
    state: AgentState,
    new_messages: tuple[ChatMessage, ...],
) -> AgentState:
    """Return state with additional messages appended."""
    if not new_messages:
        return state
    return replace(state, messages=state.messages + new_messages)


def state_to_graph_input(state: AgentState) -> GraphState:
    """Convert public AgentState to LangGraph invoke input."""
    return GraphState(
        messages=state.messages,
        tool_iteration_count=state.tool_iteration_count,
        final_response=state.final_response,
        pending_tool_calls=state.pending_tool_calls,
    )


def graph_output_to_state(output: GraphState) -> AgentState:
    """Convert LangGraph invoke output to public AgentState."""
    return AgentState(
        messages=output["messages"],
        tool_iteration_count=output["tool_iteration_count"],
        final_response=output["final_response"],
        pending_tool_calls=output["pending_tool_calls"],
    )
