"""Unit tests for demo environment assembly."""

import uuid
from pathlib import Path

from qdrant_client import QdrantClient

from knowledge_assistant.bootstrap import BootstrapSettings, build_demo_environment
from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.retrieval import RerankRetriever
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.qdrant_store import create_qdrant_vector_store


def test_build_demo_environment_returns_wired_stack() -> None:
    settings = BootstrapSettings(
        corpus_root=Path("knowledge"),
        storage_settings=StorageSettings(
            collection_name=f"bootstrap-unit-{uuid.uuid4()}",
            dense_vector_size=8,
        ),
    )
    store = create_qdrant_vector_store(
        settings.storage_settings,
        client=QdrantClient(":memory:"),
    )

    environment = build_demo_environment(settings=settings, vector_store=store)

    assert isinstance(environment, DemoEnvironment)
    assert environment.vector_store is store
    assert environment.indexing_pipeline is not None
    assert isinstance(environment.retriever, RerankRetriever)
