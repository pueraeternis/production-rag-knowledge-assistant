"""Integration test fixtures for dense retrieval."""

from collections.abc import Sequence

import pytest

from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.retrieval.embeddings import (
    QueryEmbeddingVector,
    StubQueryEmbeddingProvider,
    StubSparseQueryEmbeddingProvider,
)
from knowledge_assistant.storage.models import ChunkUpsertItem


class FakeRetriever:
    """Configurable leaf retriever fake that records the last SearchQuery."""

    def __init__(self, *, return_value: RetrievalResult) -> None:
        self._return_value = return_value
        self.last_query: SearchQuery | None = None

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        self.last_query = query
        return self._return_value


class FakeVectorStore:
    """In-memory VectorStore fake that records dense and sparse search calls."""

    def __init__(
        self,
        *,
        search_results: tuple[SearchResult, ...] = (),
        sparse_search_results: tuple[SearchResult, ...] = (),
    ) -> None:
        self.search_results = search_results
        self.sparse_search_results = sparse_search_results
        self.last_vector: Sequence[float] | None = None
        self.last_top_k: int | None = None
        self.search_dense_call_count = 0
        self.last_sparse_indices: Sequence[int] | None = None
        self.last_sparse_values: Sequence[float] | None = None
        self.last_sparse_top_k: int | None = None
        self.search_sparse_call_count = 0

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

    def search_sparse(
        self,
        *,
        indices: Sequence[int],
        values: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        self.search_sparse_call_count += 1
        self.last_sparse_indices = tuple(indices)
        self.last_sparse_values = tuple(values)
        self.last_sparse_top_k = top_k
        return self.sparse_search_results


class CountingSparseQueryEmbeddingProvider:
    """Records embed_query calls via StubSparseQueryEmbeddingProvider."""

    def __init__(self) -> None:
        self._stub = StubSparseQueryEmbeddingProvider()
        self.embed_query_call_count = 0

    def embed_query(self, text: str):
        self.embed_query_call_count += 1
        return self._stub.embed_query(text)


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
