"""Optional real-embedding dense retrieval integration test."""

import os
import uuid
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from knowledge_assistant.bootstrap import BootstrapSettings, build_demo_environment
from knowledge_assistant.core import SearchQuery
from knowledge_assistant.embeddings import EmbeddingRuntimeSettings
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.qdrant_store import create_qdrant_vector_store

pytestmark = [
    pytest.mark.embedding_model,
    pytest.mark.skipif(
        os.environ.get("RAG_EMBEDDING_ENABLE_REAL_TESTS", "").lower()
        not in {"1", "true", "yes", "on"},
        reason="set RAG_EMBEDDING_ENABLE_REAL_TESTS=true to load real embeddings",
    ),
]


def test_dense_bge_m3_retrieval_after_indexing(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "doc.md").write_text(
        "# Hybrid Retrieval\n\nHybrid retrieval combines dense and sparse vectors.\n",
        encoding="utf-8",
    )

    settings = BootstrapSettings(
        corpus_root=corpus_dir,
        storage_settings=StorageSettings(
            collection_name=f"dense-bge-{uuid.uuid4()}",
            dense_vector_size=1024,
        ),
        embedding_mode="real",
        embedding_runtime_settings=EmbeddingRuntimeSettings(
            dense_vector_size=1024,
            device="cpu",
            max_length=512,
        ),
    )
    store = create_qdrant_vector_store(
        settings.storage_settings,
        client=QdrantClient(":memory:"),
    )
    environment = build_demo_environment(settings=settings, vector_store=store)
    environment.indexing_pipeline.index_documents(
        (environment.corpus_indexing_source(),),
        rebuild=True,
    )

    dense = environment.retriever._base_retriever._dense_retriever  # type: ignore[attr-defined]
    result = dense.retrieve(SearchQuery(text="hybrid retrieval", top_k=1))  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    assert len(result.results) == 1  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
