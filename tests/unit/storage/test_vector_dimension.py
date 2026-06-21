"""Unit tests for vector dimension validation."""

import uuid

import pytest
from qdrant_client import QdrantClient

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.document import DocumentMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.source import LineRange
from knowledge_assistant.storage.collection import DEFAULT_DENSE_VECTOR_SIZE
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.exceptions import VectorDimensionError
from knowledge_assistant.storage.models import ChunkUpsertItem, SparseVector
from knowledge_assistant.storage.qdrant_store import QdrantVectorStore


def _make_item(dense_size: int) -> ChunkUpsertItem:
    return ChunkUpsertItem(
        chunk=Chunk(
            chunk_id=ChunkId(str(uuid.uuid4())),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Section",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text="chunk text",
        ),
        document_metadata=DocumentMetadata(title="Title", path="docs/title.md"),
        dense_vector=tuple(float(index) for index in range(dense_size)),
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


class TestVectorDimensionValidation:
    def test_upsert_rejects_wrong_dense_vector_length(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        with pytest.raises(
            VectorDimensionError,
            match="dense vector dimension mismatch",
        ):
            vector_store.upsert_chunks((_make_item(dense_size=3),))

    def test_search_rejects_wrong_query_vector_length(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        with pytest.raises(
            VectorDimensionError,
            match="dense vector dimension mismatch",
        ):
            vector_store.search_dense(vector=[0.1, 0.2, 0.3], top_k=1)

    def test_default_dense_vector_size_matches_collection_constant(self) -> None:
        assert StorageSettings().dense_vector_size == DEFAULT_DENSE_VECTOR_SIZE
