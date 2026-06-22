"""Demo composition root for wiring storage, indexing, and retrieval."""

from knowledge_assistant.bootstrap.chat import (
    ChatSession,
    StreamChunk,
    TurnResult,
    TurnSource,
    TurnStream,
    build_chat_session,
    execute_turn,
    execute_turn_streaming,
    initial_agent_state,
)
from knowledge_assistant.bootstrap.config import (
    REAL_PIPELINE_LABEL,
    STUB_PIPELINE_LABEL,
    BootstrapSettings,
    retrieval_pipeline_label,
)
from knowledge_assistant.bootstrap.environment import (
    DEMO_RETRIEVAL_PIPELINE_LABEL,
    DemoEnvironment,
    build_demo_environment,
)
from knowledge_assistant.bootstrap.retrievers import (
    CANONICAL_STRATEGIES,
    RetrievalStack,
    RetrievalStrategy,
    build_retrieval_stack,
    build_retriever_for_strategy,
    strategy_stack_description,
)

__all__ = (
    "CANONICAL_STRATEGIES",
    "ChatSession",
    "DEMO_RETRIEVAL_PIPELINE_LABEL",
    "REAL_PIPELINE_LABEL",
    "STUB_PIPELINE_LABEL",
    "BootstrapSettings",
    "DemoEnvironment",
    "RetrievalStack",
    "RetrievalStrategy",
    "StreamChunk",
    "TurnResult",
    "TurnSource",
    "TurnStream",
    "build_chat_session",
    "build_demo_environment",
    "build_retrieval_stack",
    "build_retriever_for_strategy",
    "execute_turn",
    "execute_turn_streaming",
    "initial_agent_state",
    "retrieval_pipeline_label",
    "strategy_stack_description",
)
