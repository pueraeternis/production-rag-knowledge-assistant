"""Unit tests for sparse query embedding providers."""

from unittest.mock import MagicMock

import pytest

from knowledge_assistant.retrieval.embeddings import (
    BgeM3SparseQueryEmbeddingProvider,
    StubSparseQueryEmbeddingProvider,
)
from knowledge_assistant.retrieval.sparse_vectors import SparseQueryVector


class TestStubSparseQueryEmbeddingProvider:
    def test_returns_valid_non_empty_sparse_query_vector(self) -> None:
        provider = StubSparseQueryEmbeddingProvider()
        vector = provider.embed_query("hybrid retrieval sparse search")

        assert isinstance(vector, SparseQueryVector)
        assert len(vector.indices) >= 1
        assert len(vector.indices) == len(vector.values)

    def test_deterministic_for_same_text(self) -> None:
        provider = StubSparseQueryEmbeddingProvider()
        text = "deterministic sparse query"

        first = provider.embed_query(text)
        second = provider.embed_query(text)

        assert first == second

    def test_different_text_produces_different_vectors(self) -> None:
        provider = StubSparseQueryEmbeddingProvider()

        first = provider.embed_query("alpha beta gamma")
        second = provider.embed_query("delta epsilon zeta")

        assert first != second

    def test_strips_and_tokenizes_on_whitespace(self) -> None:
        provider = StubSparseQueryEmbeddingProvider()
        spaced = provider.embed_query("  term one   term two  ")
        compact = provider.embed_query("term one term two")

        assert spaced == compact

    def test_values_are_normalized(self) -> None:
        provider = StubSparseQueryEmbeddingProvider()
        vector = provider.embed_query("normalize values check")

        norm = sum(value * value for value in vector.values) ** 0.5
        assert norm == pytest.approx(1.0)


class TestBgeM3SparseQueryEmbeddingProvider:
    def test_delegates_to_runtime_and_returns_sparse_query_vector(self) -> None:
        runtime = MagicMock()
        runtime.embed_query_sparse.return_value = ((10, 20), (0.5, 0.25))
        provider = BgeM3SparseQueryEmbeddingProvider(runtime=runtime)

        vector = provider.embed_query("hybrid search")

        runtime.embed_query_sparse.assert_called_once_with("hybrid search")
        assert vector == SparseQueryVector(indices=(10, 20), values=(0.5, 0.25))
