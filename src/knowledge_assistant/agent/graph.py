"""LangGraph agent graph construction and turn execution."""

# pyright: reportUnknownMemberType=false

from __future__ import annotations

from typing import Any, Literal, cast

from langgraph.graph import (  # pyright: ignore[reportMissingTypeStubs]
    END,
    START,
    StateGraph,
)

from knowledge_assistant.agent.config import AgentSettings
from knowledge_assistant.agent.exceptions import UnknownToolError
from knowledge_assistant.agent.state import (
    AgentState,
    GraphState,
    graph_output_to_state,
    state_to_graph_input,
)
from knowledge_assistant.agent.tools import ToolRegistry, tool_error_content
from knowledge_assistant.llm.config import GenerationSettings
from knowledge_assistant.llm.messages import ChatMessage, ChatRole
from knowledge_assistant.llm.protocol import LLMClient

_MAX_ITERATIONS_MESSAGE = (
    "Tool iteration limit reached. Unable to complete additional tool calls."
)


def _assistant_message_from_result(content: str | None) -> ChatMessage:
    return ChatMessage(role=ChatRole.ASSISTANT, content=content)


def build_agent_graph(
    llm_client: LLMClient,
    tool_registry: ToolRegistry,
    settings: AgentSettings | None = None,
) -> Any:
    """Compile the LangGraph workflow for conversational RAG orchestration."""
    agent_settings = settings or AgentSettings()
    generation_settings = GenerationSettings()

    def agent_node(state: GraphState) -> dict[str, object]:
        result = llm_client.chat(
            state["messages"],
            settings=generation_settings,
            tools=tool_registry.definitions(),
        )
        assistant_message = _assistant_message_from_result(result.content)
        update: dict[str, object] = {
            "messages": (assistant_message,),
            "pending_tool_calls": result.tool_calls,
        }
        if not result.tool_calls:
            update["final_response"] = result.content
        return update

    def tool_node(state: GraphState) -> dict[str, object]:
        tool_messages: list[ChatMessage] = []
        for call in state["pending_tool_calls"]:
            try:
                tool_messages.append(tool_registry.dispatch(call))
            except UnknownToolError as exc:
                tool_messages.append(
                    ChatMessage(
                        role=ChatRole.TOOL,
                        content=tool_error_content(
                            error="unknown_tool",
                            detail=f"unknown tool: {exc.tool_name}",
                        ),
                        tool_call_id=call.id,
                    ),
                )
        return {
            "messages": tuple(tool_messages),
            "pending_tool_calls": (),
            "tool_iteration_count": state["tool_iteration_count"] + 1,
        }

    def max_iterations_node(state: GraphState) -> dict[str, object]:
        _ = state
        refusal = ChatMessage(
            role=ChatRole.ASSISTANT,
            content=_MAX_ITERATIONS_MESSAGE,
        )
        return {
            "messages": (refusal,),
            "pending_tool_calls": (),
            "final_response": _MAX_ITERATIONS_MESSAGE,
        }

    def should_continue(
        state: GraphState,
    ) -> Literal["tool_node", "max_iterations", "__end__"]:
        if not state["pending_tool_calls"]:
            return "__end__"
        if state["tool_iteration_count"] >= agent_settings.max_tool_iterations:
            return "max_iterations"
        return "tool_node"

    workflow = StateGraph(GraphState)
    workflow.add_node("agent_node", agent_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("max_iterations", max_iterations_node)
    workflow.add_edge(START, "agent_node")
    workflow.add_conditional_edges(
        "agent_node",
        should_continue,
        {
            "tool_node": "tool_node",
            "max_iterations": "max_iterations",
            "__end__": END,
        },
    )
    workflow.add_edge("tool_node", "agent_node")
    workflow.add_edge("max_iterations", END)
    return workflow.compile()


def run_turn(
    *,
    state: AgentState,
    user_message: str,
    llm_client: LLMClient,
    tool_registry: ToolRegistry,
    settings: AgentSettings | None = None,
) -> AgentState:
    """Append user message, invoke LangGraph, and return updated state."""
    if not user_message.strip():
        msg = "user_message must be non-empty"
        raise ValueError(msg)

    user_chat_message = ChatMessage(role=ChatRole.USER, content=user_message)
    input_state = AgentState(
        messages=(*state.messages, user_chat_message),
        tool_iteration_count=state.tool_iteration_count,
        final_response=None,
        pending_tool_calls=(),
    )

    graph = build_agent_graph(
        llm_client,
        tool_registry,
        settings=settings,
    )
    output = cast("GraphState", graph.invoke(state_to_graph_input(input_state)))
    return graph_output_to_state(output)
