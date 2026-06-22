"""Optional real-model smoke tests for BGE-M3 sparse runtime."""

import os

import pytest

from knowledge_assistant.embeddings import (
    EmbeddingRuntimeSettings,
    create_dense_embedding_runtime,
)

pytestmark = [
    pytest.mark.embedding_model,
    pytest.mark.skipif(
        os.environ.get("RAG_EMBEDDING_ENABLE_REAL_TESTS", "").lower()
        not in {"1", "true", "yes", "on"},
        reason="set RAG_EMBEDDING_ENABLE_REAL_TESTS=true to load real embeddings",
    ),
]


def test_bge_m3_sparse_runtime_smoke_passage_and_query() -> None:
    settings = EmbeddingRuntimeSettings(
        model_name="BAAI/bge-m3",
        device="cpu",
        batch_size=2,
        max_length=512,
        normalize_embeddings=True,
        dense_vector_size=1024,
    )
    runtime = create_dense_embedding_runtime(settings)

    passage_sparse = runtime.embed_passages_sparse(
        ("Hybrid retrieval combines dense and sparse search.",),
    )
    query_indices, query_values = runtime.embed_query_sparse(
        "What is hybrid retrieval?",
    )

    assert len(passage_sparse) == 1
    passage_indices, passage_values = passage_sparse[0]
    assert passage_indices == tuple(sorted(passage_indices))
    assert len(passage_indices) > 0
    assert len(passage_indices) == len(passage_values)
    assert query_indices == tuple(sorted(query_indices))
    assert len(query_indices) > 0
    assert len(query_values) == len(query_indices)
