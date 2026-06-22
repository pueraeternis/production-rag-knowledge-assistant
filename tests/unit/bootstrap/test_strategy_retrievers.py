"""Unit tests for bootstrap strategy retriever assembly."""

import uuid
from pathlib import Path

from qdrant_client import QdrantClient

from knowledge_assistant.bootstrap import (
    CANONICAL_STRATEGIES,
    build_demo_environment,
    build_retriever_for_strategy,
)
from knowledge_assistant.bootstrap.config import BootstrapSettings
from knowledge_assistant.retrieval import (
    DenseRetriever,
    FusionRetriever,
    RerankRetriever,
    SparseRetriever,
    StubSparseQueryEmbeddingProvider,
)
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.qdrant_store import create_qdrant_vector_store


def test_canonical_strategies_order() -> None:
    assert CANONICAL_STRATEGIES == ("dense", "sparse", "fusion", "rerank")


def test_build_retriever_for_strategy_returns_expected_orchestrators() -> None:
    settings = BootstrapSettings(
        corpus_root=Path("knowledge"),
        storage_settings=StorageSettings(
            collection_name=f"strategy-unit-{uuid.uuid4()}",
            dense_vector_size=8,
        ),
    )
    store = create_qdrant_vector_store(
        settings.storage_settings,
        client=QdrantClient(":memory:"),
    )
    environment = build_demo_environment(settings=settings, vector_store=store)

    dense = build_retriever_for_strategy(environment, "dense")
    sparse = build_retriever_for_strategy(environment, "sparse")
    fusion = build_retriever_for_strategy(environment, "fusion")
    rerank = build_retriever_for_strategy(environment, "rerank")

    assert isinstance(dense, DenseRetriever)
    assert isinstance(sparse, SparseRetriever)
    assert isinstance(fusion, FusionRetriever)
    assert isinstance(rerank, RerankRetriever)


def test_strategy_retrievers_share_vector_store() -> None:
    settings = BootstrapSettings(
        corpus_root=Path("knowledge"),
        storage_settings=StorageSettings(
            collection_name=f"strategy-unit-{uuid.uuid4()}",
            dense_vector_size=8,
        ),
    )
    store = create_qdrant_vector_store(
        settings.storage_settings,
        client=QdrantClient(":memory:"),
    )
    environment = build_demo_environment(settings=settings, vector_store=store)
    stack = environment.retrieval_stack

    assert stack.dense_retriever._vector_store is store  # pyright: ignore[reportPrivateUsage]
    assert stack.sparse_retriever._vector_store is store  # pyright: ignore[reportPrivateUsage]
    assert isinstance(
        stack.sparse_retriever._embedding_provider,  # pyright: ignore[reportPrivateUsage]
        StubSparseQueryEmbeddingProvider,
    )
    assert environment.retriever is stack.rerank_retriever
