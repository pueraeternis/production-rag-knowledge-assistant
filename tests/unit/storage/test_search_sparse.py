"""Unit tests for QdrantVectorStore.search_sparse."""

import uuid
from unittest.mock import MagicMock

import pytest

from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.exceptions import CollectionNotFoundError
from knowledge_assistant.storage.qdrant_store import QdrantVectorStore


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.collection_exists.return_value = True
    return client


@pytest.fixture
def vector_store(mock_client: MagicMock) -> QdrantVectorStore:
    return QdrantVectorStore(
        client=mock_client,
        settings=StorageSettings(collection_name="test-collection"),
    )


class TestSearchSparse:
    def test_returns_empty_tuple_for_empty_indices(
        self,
        vector_store: QdrantVectorStore,
        mock_client: MagicMock,
    ) -> None:
        results = vector_store.search_sparse(indices=(), values=(), top_k=3)

        assert results == ()
        mock_client.query_points.assert_not_called()

    def test_raises_when_collection_missing(self) -> None:
        client = MagicMock()
        client.collection_exists.return_value = False
        store = QdrantVectorStore(
            client=client,
            settings=StorageSettings(collection_name=f"missing-{uuid.uuid4()}"),
        )

        with pytest.raises(CollectionNotFoundError):
            store.search_sparse(indices=(0,), values=(1.0,), top_k=1)

    def test_raises_when_top_k_invalid(self, vector_store: QdrantVectorStore) -> None:
        with pytest.raises(ValueError, match="top_k must be >= 1"):
            vector_store.search_sparse(indices=(0,), values=(1.0,), top_k=0)

    def test_rejects_length_mismatch(self, vector_store: QdrantVectorStore) -> None:
        with pytest.raises(ValueError, match="same length"):
            vector_store.search_sparse(indices=(0, 1), values=(1.0,), top_k=1)

    def test_rejects_duplicate_indices(self, vector_store: QdrantVectorStore) -> None:
        with pytest.raises(ValueError, match="unique"):
            vector_store.search_sparse(indices=(0, 0), values=(1.0, 0.5), top_k=1)

    def test_rejects_negative_indices(self, vector_store: QdrantVectorStore) -> None:
        with pytest.raises(ValueError, match=">= 0"):
            vector_store.search_sparse(indices=(-1,), values=(1.0,), top_k=1)
