"""Unit tests for SearchResult.source population in storage search paths."""

import uuid
from unittest.mock import MagicMock

from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.qdrant_store import QdrantVectorStore


def _sample_payload() -> dict[str, object]:
    return {
        "document_id": "doc-1",
        "document_title": "Guide",
        "document_path": "docs/guide.md",
        "source_uri": None,
        "section_title": "Overview",
        "start_line": 1,
        "end_line": 5,
        "chunk_index": 0,
        "text": "sample chunk text",
    }


class TestSearchResultSourcePopulation:
    def test_search_dense_populates_source_reference(self) -> None:
        client = MagicMock()
        client.collection_exists.return_value = True
        chunk_id = str(uuid.uuid4())
        scored_point = MagicMock()
        scored_point.id = chunk_id
        scored_point.score = 0.91
        scored_point.payload = _sample_payload()
        response = MagicMock()
        response.points = [scored_point]
        client.query_points.return_value = response

        store = QdrantVectorStore(
            client=client,
            settings=StorageSettings(
                collection_name="test-collection",
                dense_vector_size=4,
            ),
        )
        results = store.search_dense(vector=[1.0, 0.0, 0.0, 0.0], top_k=1)

        assert len(results) == 1
        assert results[0].source == SourceReference(
            document_title="Guide",
            document_path="docs/guide.md",
            section_title="Overview",
            line_range=LineRange(start_line=1, end_line=5),
        )

    def test_search_sparse_populates_source_reference(self) -> None:
        client = MagicMock()
        client.collection_exists.return_value = True
        chunk_id = str(uuid.uuid4())
        scored_point = MagicMock()
        scored_point.id = chunk_id
        scored_point.score = 0.77
        scored_point.payload = _sample_payload()
        response = MagicMock()
        response.points = [scored_point]
        client.query_points.return_value = response

        store = QdrantVectorStore(
            client=client,
            settings=StorageSettings(
                collection_name="test-collection",
                dense_vector_size=4,
            ),
        )
        results = store.search_sparse(indices=(0,), values=(1.0,), top_k=1)

        assert len(results) == 1
        assert results[0].source.document_path == "docs/guide.md"
        assert results[0].source.document_title == "Guide"
