"""Bootstrap wiring tests for real embedding provider mode."""

import uuid
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

from qdrant_client import QdrantClient

from knowledge_assistant.bootstrap import BootstrapSettings, build_demo_environment
from knowledge_assistant.bootstrap.config import (
    REAL_PIPELINE_LABEL,
    STUB_PIPELINE_LABEL,
)
from knowledge_assistant.embeddings import EmbeddingRuntimeSettings
from knowledge_assistant.indexing import (
    BgeM3EmbeddingProvider,
    BgeM3SparseEmbeddingProvider,
    StubEmbeddingProvider,
    StubSparseEmbeddingProvider,
)
from knowledge_assistant.retrieval import (
    BgeM3QueryEmbeddingProvider,
    BgeM3SparseQueryEmbeddingProvider,
    StubQueryEmbeddingProvider,
    StubSparseQueryEmbeddingProvider,
)
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.qdrant_store import create_qdrant_vector_store


def _memory_settings() -> BootstrapSettings:
    return BootstrapSettings(
        corpus_root=Path("knowledge"),
        storage_settings=StorageSettings(
            collection_name=f"bootstrap-real-{uuid.uuid4()}",
            dense_vector_size=8,
        ),
    )


def test_stub_mode_uses_stub_providers_by_default() -> None:
    settings = _memory_settings()
    store = create_qdrant_vector_store(
        settings.storage_settings,
        client=QdrantClient(":memory:"),
    )

    environment = build_demo_environment(settings=settings, vector_store=store)

    assert settings.embedding_mode == "stub"
    assert isinstance(
        environment.indexing_pipeline._embedding_provider,  # pyright: ignore[reportPrivateUsage]
        StubEmbeddingProvider,
    )
    assert isinstance(
        environment.indexing_pipeline._sparse_embedding_provider,  # pyright: ignore[reportPrivateUsage]
        StubSparseEmbeddingProvider,
    )
    dense = environment.retriever._base_retriever._dense_retriever  # type: ignore[attr-defined]
    sparse = environment.retriever._base_retriever._sparse_retriever  # type: ignore[attr-defined]
    assert isinstance(
        dense._embedding_provider,  # pyright: ignore[reportPrivateUsage, reportUnknownMemberType]
        StubQueryEmbeddingProvider,
    )
    assert isinstance(
        sparse._embedding_provider,  # pyright: ignore[reportPrivateUsage, reportUnknownMemberType]
        StubSparseQueryEmbeddingProvider,
    )
    assert environment.pipeline_label == STUB_PIPELINE_LABEL


@patch(
    "knowledge_assistant.bootstrap.environment.create_shared_dense_embedding_runtime",
)
def test_real_mode_wires_shared_runtime_to_both_providers(
    create_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    create_runtime.return_value = runtime
    settings = BootstrapSettings(
        corpus_root=Path("knowledge"),
        storage_settings=StorageSettings(
            collection_name=f"bootstrap-real-{uuid.uuid4()}",
            dense_vector_size=8,
        ),
        embedding_mode="real",
        embedding_runtime_settings=EmbeddingRuntimeSettings(
            dense_vector_size=8,
            device="cpu",
        ),
    )
    store = create_qdrant_vector_store(
        settings.storage_settings,
        client=QdrantClient(":memory:"),
    )

    environment = build_demo_environment(settings=settings, vector_store=store)

    create_runtime.assert_called_once_with(settings.embedding_runtime_settings)
    indexing_provider = environment.indexing_pipeline._embedding_provider  # pyright: ignore[reportPrivateUsage]
    sparse_indexing_provider = environment.indexing_pipeline._sparse_embedding_provider  # pyright: ignore[reportPrivateUsage]
    dense = environment.retriever._base_retriever._dense_retriever  # type: ignore[attr-defined]
    sparse = environment.retriever._base_retriever._sparse_retriever  # type: ignore[attr-defined]
    query_provider = cast(
        "BgeM3QueryEmbeddingProvider",
        dense._embedding_provider,  # pyright: ignore[reportPrivateUsage, reportUnknownMemberType]
    )
    sparse_query_provider = cast(
        "BgeM3SparseQueryEmbeddingProvider",
        sparse._embedding_provider,  # pyright: ignore[reportPrivateUsage, reportUnknownMemberType]
    )
    assert isinstance(indexing_provider, BgeM3EmbeddingProvider)
    assert isinstance(sparse_indexing_provider, BgeM3SparseEmbeddingProvider)
    assert isinstance(query_provider, BgeM3QueryEmbeddingProvider)
    assert isinstance(sparse_query_provider, BgeM3SparseQueryEmbeddingProvider)
    assert indexing_provider.runtime is runtime
    assert sparse_indexing_provider.runtime is runtime
    assert query_provider.runtime is runtime
    assert sparse_query_provider.runtime is runtime
    assert environment.pipeline_label == REAL_PIPELINE_LABEL
