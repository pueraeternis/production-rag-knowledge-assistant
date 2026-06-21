"""Integration test fixtures for dense retrieval."""

from collections.abc import Sequence

import pytest

from knowledge_assistant.core.retrieval import SearchResult
from knowledge_assistant.retrieval.embeddings import (
    QueryEmbeddingVector,
    StubQueryEmbeddingProvider,
)
from knowledge_assistant.storage.models import ChunkUpsertItem


class FakeVectorStore:
    """In-memory VectorStore fake that records dense search calls."""

    def __init__(
        self,
        *,
        search_results: tuple[SearchResult, ...] = (),
    ) -> None:
        self.search_results = search_results
        self.last_vector: Sequence[float] | None = None
        self.last_top_k: int | None = None
        self.search_dense_call_count = 0

    def create_collection(self) -> None:
        pass

    def delete_collection(self) -> None:
        pass

    def collection_exists(self) -> bool:
        return False

    def upsert_chunks(self, items: tuple[ChunkUpsertItem, ...]) -> None:
        _ = items

    def search_dense(
        self,
        *,
        vector: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        self.search_dense_call_count += 1
        self.last_vector = tuple(vector)
        self.last_top_k = top_k
        return self.search_results


class CountingQueryEmbeddingProvider:
    """Records embed_query calls while delegating to StubQueryEmbeddingProvider."""

    def __init__(self, *, dimension: int = 1024) -> None:
        self._stub = StubQueryEmbeddingProvider(dimension=dimension)
        self.embed_query_call_count = 0

    def embed_query(self, text: str) -> QueryEmbeddingVector:
        self.embed_query_call_count += 1
        return self._stub.embed_query(text)


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()
