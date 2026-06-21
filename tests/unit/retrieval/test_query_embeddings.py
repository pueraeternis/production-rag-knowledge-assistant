"""Unit tests for query embedding providers."""

import math

import pytest

from knowledge_assistant.retrieval.embeddings import StubQueryEmbeddingProvider


class TestStubQueryEmbeddingProvider:
    def test_returns_vector_of_expected_dimension(self) -> None:
        provider = StubQueryEmbeddingProvider(dimension=8)
        vector = provider.embed_query("hybrid retrieval")
        assert len(vector) == 8

    def test_same_query_text_returns_same_vector(self) -> None:
        provider = StubQueryEmbeddingProvider(dimension=16)
        vector_a = provider.embed_query("same query")
        vector_b = provider.embed_query("same query")
        assert vector_a == vector_b

    def test_vector_is_l2_normalized(self) -> None:
        provider = StubQueryEmbeddingProvider(dimension=16)
        vector = provider.embed_query("normalized query")
        norm = math.sqrt(sum(value * value for value in vector))
        assert norm == pytest.approx(1.0)

    def test_default_dimension_is_1024(self) -> None:
        provider = StubQueryEmbeddingProvider()
        vector = provider.embed_query("default dimension")
        assert len(vector) == 1024
