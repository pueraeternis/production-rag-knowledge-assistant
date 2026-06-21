"""Unit tests for indexing embeddings."""

import math

from knowledge_assistant.indexing.embeddings import (
    StubEmbeddingProvider,
    sparse_placeholder_vector,
)
from knowledge_assistant.storage.models import SparseVector


class TestStubEmbeddingProvider:
    def test_returns_expected_dimension(self) -> None:
        provider = StubEmbeddingProvider(dimension=16)
        vectors = provider.embed_texts(("hello", "world"))

        assert len(vectors) == 2
        assert all(len(vector) == 16 for vector in vectors)

    def test_vectors_are_l2_normalized(self) -> None:
        provider = StubEmbeddingProvider(dimension=32)
        vector = provider.embed_texts(("normalize me",))[0]
        norm = math.sqrt(sum(value * value for value in vector))

        assert math.isclose(norm, 1.0, rel_tol=1e-6)

    def test_same_text_produces_same_vector(self) -> None:
        provider = StubEmbeddingProvider(dimension=64)
        first = provider.embed_texts(("repeatable",))[0]
        second = provider.embed_texts(("repeatable",))[0]

        assert first == second


class TestSparsePlaceholderVector:
    def test_returns_constant_sparse_vector(self) -> None:
        vector = sparse_placeholder_vector()

        assert vector == SparseVector(indices=(0,), values=(1.0,))

    def test_is_deterministic(self) -> None:
        assert sparse_placeholder_vector() == sparse_placeholder_vector()
