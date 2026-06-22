"""VectorStore protocol defining the storage boundary contract."""

from collections.abc import Sequence
from typing import Protocol

from knowledge_assistant.core.retrieval import SearchResult
from knowledge_assistant.storage.models import ChunkUpsertItem


class VectorStore(Protocol):
    """Storage contract for chunk persistence and dense vector search."""

    def create_collection(self) -> None:
        """Create collection with dense and sparse vector schema."""
        ...

    def delete_collection(self) -> None:
        """Delete the collection if it exists. Idempotent."""
        ...

    def collection_exists(self) -> bool:
        """Return whether the collection currently exists."""
        ...

    def count_points(self) -> int:
        """Return stored point count; zero when the collection does not exist."""
        ...

    def upsert_chunks(self, items: tuple[ChunkUpsertItem, ...]) -> None:
        """Insert or update chunk points with vectors and payloads."""
        ...

    def search_dense(
        self,
        *,
        vector: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        """Search the dense vector and return chunks with similarity scores."""
        ...

    def search_sparse(
        self,
        *,
        indices: Sequence[int],
        values: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        """Search the sparse named vector and return chunks with scores."""
        ...
