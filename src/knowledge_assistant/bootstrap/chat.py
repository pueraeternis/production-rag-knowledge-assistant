"""Chat session assembly and turn execution facades."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from knowledge_assistant.agent.config import AgentSettings
from knowledge_assistant.agent.graph import run_turn, run_turn_streaming
from knowledge_assistant.agent.prompts import SYSTEM_PROMPT
from knowledge_assistant.agent.state import AgentState
from knowledge_assistant.agent.tools import ToolRegistry
from knowledge_assistant.agent.turn import TurnResult, TurnSource, TurnStream
from knowledge_assistant.agent.wiring import build_default_tool_registry
from knowledge_assistant.bootstrap.config import BootstrapSettings
from knowledge_assistant.bootstrap.environment import (
    DemoEnvironment,
    build_demo_environment,
)
from knowledge_assistant.llm.config import LlmSettings
from knowledge_assistant.llm.messages import ChatMessage, ChatRole, StreamChunk
from knowledge_assistant.llm.openai_client import OpenAICompatibleLLMClient
from knowledge_assistant.llm.protocol import LLMClient
from knowledge_assistant.mcp_server.config import McpServerSettings

if TYPE_CHECKING:
    from knowledge_assistant.storage import VectorStore


@dataclass(frozen=True, slots=True)
class ChatSession:
    """Assembled chat dependencies for one CLI invocation."""

    environment: DemoEnvironment
    llm_client: LLMClient
    tool_registry: ToolRegistry
    agent_settings: AgentSettings
    llm_settings: LlmSettings


def build_chat_session(
    *,
    bootstrap_settings: BootstrapSettings | None = None,
    llm_settings: LlmSettings | None = None,
    llm_client: LLMClient | None = None,
    vector_store: VectorStore | None = None,
    agent_settings: AgentSettings | None = None,
) -> ChatSession:
    """Assemble demo environment, LLM client, and agent tool registry for chat."""
    environment = build_demo_environment(
        settings=bootstrap_settings,
        vector_store=vector_store,
    )
    resolved_llm_settings = llm_settings or LlmSettings.from_env()
    resolved_llm_client = llm_client or OpenAICompatibleLLMClient(
        resolved_llm_settings,
    )
    tool_registry = build_default_tool_registry(
        retriever=environment.retriever,
        pipeline=environment.indexing_pipeline,
        settings=McpServerSettings(),
    )
    return ChatSession(
        environment=environment,
        llm_client=resolved_llm_client,
        tool_registry=tool_registry,
        agent_settings=agent_settings or AgentSettings(),
        llm_settings=resolved_llm_settings,
    )


def initial_agent_state() -> AgentState:
    """Return a fresh in-memory state with the RAG system prompt."""
    return AgentState(
        messages=(ChatMessage(role=ChatRole.SYSTEM, content=SYSTEM_PROMPT),),
    )


def execute_turn(
    session: ChatSession,
    state: AgentState,
    message: str,
) -> TurnResult:
    """Run one non-streaming conversation turn."""
    return run_turn(
        state=state,
        user_message=message,
        llm_client=session.llm_client,
        tool_registry=session.tool_registry,
        settings=session.agent_settings,
    )


def execute_turn_streaming(
    session: ChatSession,
    state: AgentState,
    message: str,
) -> TurnStream:
    """Run one streaming conversation turn."""
    return run_turn_streaming(
        state=state,
        user_message=message,
        llm_client=session.llm_client,
        tool_registry=session.tool_registry,
        settings=session.agent_settings,
    )


__all__ = (
    "ChatSession",
    "StreamChunk",
    "TurnResult",
    "TurnSource",
    "TurnStream",
    "build_chat_session",
    "execute_turn",
    "execute_turn_streaming",
    "initial_agent_state",
)
