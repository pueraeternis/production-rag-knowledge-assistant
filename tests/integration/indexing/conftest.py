"""Integration test fixtures for indexing pipeline."""

from collections.abc import Sequence

import pytest

from knowledge_assistant.core.retrieval import SearchResult
from knowledge_assistant.storage.models import ChunkUpsertItem


class FakeVectorStore:
    """In-memory VectorStore fake that records method call order."""

    def __init__(self, *, collection_exists: bool = False) -> None:
        self.collection_exists_value = collection_exists
        self.calls: list[str] = []
        self.upserted_items: tuple[ChunkUpsertItem, ...] = ()

    def create_collection(self) -> None:
        self.calls.append("create_collection")
        self.collection_exists_value = True

    def delete_collection(self) -> None:
        self.calls.append("delete_collection")
        self.collection_exists_value = False

    def collection_exists(self) -> bool:
        self.calls.append("collection_exists")
        return self.collection_exists_value

    def count_points(self) -> int:
        self.calls.append("count_points")
        if not self.collection_exists_value:
            return 0
        return len(self.upserted_items)

    def upsert_chunks(self, items: tuple[ChunkUpsertItem, ...]) -> None:
        self.calls.append("upsert_chunks")
        self.upserted_items = items

    def search_dense(
        self,
        *,
        vector: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        _ = vector
        _ = top_k
        return ()

    def search_sparse(
        self,
        *,
        indices: Sequence[int],
        values: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        _ = indices
        _ = values
        _ = top_k
        return ()


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore(collection_exists=False)
