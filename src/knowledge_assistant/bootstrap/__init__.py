"""Demo composition root for wiring storage, indexing, and retrieval."""

from knowledge_assistant.bootstrap.config import BootstrapSettings
from knowledge_assistant.bootstrap.environment import (
    DEMO_RETRIEVAL_PIPELINE_LABEL,
    DemoEnvironment,
    build_demo_environment,
)

__all__ = (
    "BootstrapSettings",
    "DEMO_RETRIEVAL_PIPELINE_LABEL",
    "DemoEnvironment",
    "build_demo_environment",
)
