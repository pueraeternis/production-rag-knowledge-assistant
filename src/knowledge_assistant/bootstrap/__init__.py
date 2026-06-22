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

__all__ = (
    "BootstrapSettings",
    "DEMO_RETRIEVAL_PIPELINE_LABEL",
    "DemoEnvironment",
    "REAL_PIPELINE_LABEL",
    "STUB_PIPELINE_LABEL",
    "build_demo_environment",
    "retrieval_pipeline_label",
)
