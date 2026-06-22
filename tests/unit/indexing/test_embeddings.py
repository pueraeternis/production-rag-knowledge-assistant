"""Unit tests for indexing embeddings."""

import math
from unittest.mock import MagicMock

from knowledge_assistant.indexing.embeddings import (
    BgeM3SparseEmbeddingProvider,
    StubEmbeddingProvider,
    StubSparseEmbeddingProvider,
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


class TestStubSparseEmbeddingProvider:
    def test_returns_distinct_vectors_for_distinct_texts(self) -> None:
        provider = StubSparseEmbeddingProvider()
        first, second = provider.embed_sparse_texts(("alpha text", "beta text"))

        assert first != second
        assert len(first.indices) == len(first.values)
        assert len(first.indices) > 0

    def test_same_text_is_deterministic(self) -> None:
        provider = StubSparseEmbeddingProvider()
        first = provider.embed_sparse_texts(("repeatable sparse",))[0]
        second = provider.embed_sparse_texts(("repeatable sparse",))[0]

        assert first == second


class TestBgeM3SparseEmbeddingProvider:
    def test_delegates_to_runtime(self) -> None:
        runtime = MagicMock()
        runtime.embed_passages_sparse.return_value = (((10, 20), (0.5, 0.25)),)
        provider = BgeM3SparseEmbeddingProvider(runtime=runtime)

        vectors = provider.embed_sparse_texts(("chunk text",))

        runtime.embed_passages_sparse.assert_called_once_with(("chunk text",))
        assert vectors[0] == SparseVector(indices=(10, 20), values=(0.5, 0.25))


class TestSparsePlaceholderVector:
    def test_returns_constant_sparse_vector(self) -> None:
        vector = sparse_placeholder_vector()

        assert vector == SparseVector(indices=(0,), values=(1.0,))

    def test_is_deterministic(self) -> None:
        assert sparse_placeholder_vector() == sparse_placeholder_vector()
