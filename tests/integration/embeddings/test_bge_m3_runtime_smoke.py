"""Optional real-model smoke tests for BGE-M3 runtime."""

import math
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


def test_bge_m3_runtime_smoke_embed_query_and_passage() -> None:
    settings = EmbeddingRuntimeSettings(
        model_name="BAAI/bge-m3",
        device="cpu",
        batch_size=2,
        max_length=512,
        normalize_embeddings=True,
        dense_vector_size=1024,
    )
    runtime = create_dense_embedding_runtime(settings)

    query_vector = runtime.embed_query("What is hybrid retrieval?")
    passage_vectors = runtime.embed_passages(
        ("Hybrid retrieval combines dense and sparse search.",),
    )

    assert len(query_vector) == 1024
    assert len(passage_vectors) == 1
    assert len(passage_vectors[0]) == 1024

    query_norm = math.sqrt(sum(value * value for value in query_vector))
    passage_norm = math.sqrt(sum(value * value for value in passage_vectors[0]))
    assert math.isclose(query_norm, 1.0, rel_tol=1e-4)
    assert math.isclose(passage_norm, 1.0, rel_tol=1e-4)
