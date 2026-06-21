"""Unit tests for sparse query embedding providers."""

import pytest

from knowledge_assistant.retrieval.embeddings import StubSparseQueryEmbeddingProvider
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
