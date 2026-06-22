"""Demo composition root for wiring storage, indexing, and retrieval."""

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
    "DEMO_RETRIEVAL_PIPELINE_LABEL",
    "REAL_PIPELINE_LABEL",
    "STUB_PIPELINE_LABEL",
    "BootstrapSettings",
    "DemoEnvironment",
    "RetrievalStack",
    "RetrievalStrategy",
    "build_demo_environment",
    "build_retrieval_stack",
    "build_retriever_for_strategy",
    "retrieval_pipeline_label",
    "strategy_stack_description",
)
