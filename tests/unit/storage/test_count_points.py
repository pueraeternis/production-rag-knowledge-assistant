"""Unit tests for VectorStore.count_points semantics."""

import uuid

from qdrant_client import QdrantClient

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.document import DocumentMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.source import LineRange
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.models import ChunkUpsertItem, SparseVector
from knowledge_assistant.storage.qdrant_store import QdrantVectorStore


def _make_item(
    *,
    chunk_id: str,
    dense_vector: tuple[float, ...],
    text: str,
) -> ChunkUpsertItem:
    return ChunkUpsertItem(
        chunk=Chunk(
            chunk_id=ChunkId(chunk_id),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Overview",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text=text,
        ),
        document_metadata=DocumentMetadata(
            title="Guide",
            path="docs/guide.md",
            source_uri=None,
        ),
        dense_vector=dense_vector,
        sparse_vector=SparseVector(indices=(0, 2), values=(0.8, 0.2)),
    )


def test_count_points_returns_zero_when_collection_missing() -> None:
    settings = StorageSettings(
        collection_name=f"count-points-missing-{uuid.uuid4()}",
        dense_vector_size=8,
    )
    store = QdrantVectorStore(client=QdrantClient(":memory:"), settings=settings)

    assert store.count_points() == 0


def test_count_points_returns_upserted_count_after_indexing() -> None:
    settings = StorageSettings(
        collection_name=f"count-points-present-{uuid.uuid4()}",
        dense_vector_size=8,
    )
    store = QdrantVectorStore(client=QdrantClient(":memory:"), settings=settings)
    store.create_collection()

    vector = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
    items: tuple[ChunkUpsertItem, ...] = (
        _make_item(chunk_id=str(uuid.uuid4()), text="alpha", dense_vector=vector),
        _make_item(chunk_id=str(uuid.uuid4()), text="beta", dense_vector=vector),
    )
    store.upsert_chunks(items)

    assert store.count_points() == 2
