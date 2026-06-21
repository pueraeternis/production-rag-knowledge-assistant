"""Unit tests for ChunkId to Qdrant point ID conversion."""

import uuid

import pytest
from qdrant_client import QdrantClient

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.document import DocumentMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.source import LineRange
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.exceptions import InvalidChunkIdError
from knowledge_assistant.storage.models import ChunkUpsertItem, SparseVector
from knowledge_assistant.storage.qdrant_store import QdrantVectorStore


def _make_item(*, chunk_id: str) -> ChunkUpsertItem:
    return ChunkUpsertItem(
        chunk=Chunk(
            chunk_id=ChunkId(chunk_id),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Section",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text="chunk text",
        ),
        document_metadata=DocumentMetadata(title="Title", path="docs/title.md"),
        dense_vector=(1.0, 0.0, 0.0, 0.0),
        sparse_vector=SparseVector(indices=(0,), values=(0.5,)),
    )


@pytest.fixture
def vector_store() -> QdrantVectorStore:
    settings = StorageSettings(
        collection_name=f"test-{uuid.uuid4()}",
        dense_vector_size=4,
    )
    store = QdrantVectorStore(client=QdrantClient(":memory:"), settings=settings)
    store.create_collection()
    return store


class TestChunkIdPointIdConversion:
    def test_valid_uuid_chunk_id_round_trips_through_search(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        chunk_id = str(uuid.uuid4())
        vector_store.upsert_chunks((_make_item(chunk_id=chunk_id),))

        results = vector_store.search_dense(vector=[1.0, 0.0, 0.0, 0.0], top_k=1)

        assert len(results) == 1
        assert results[0].chunk.chunk_id == ChunkId(chunk_id)

    def test_non_uuid_chunk_id_raises_invalid_chunk_id_error(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        with pytest.raises(
            InvalidChunkIdError, match="chunk_id must be a valid UUID string"
        ):
            vector_store.upsert_chunks((_make_item(chunk_id="not-a-uuid"),))
