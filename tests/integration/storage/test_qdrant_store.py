"""Integration tests for QdrantVectorStore."""

import uuid

import pytest
from qdrant_client import QdrantClient, models

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.document import DocumentMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.storage.collection import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from knowledge_assistant.storage.exceptions import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    InvalidChunkIdError,
)
from knowledge_assistant.storage.mapping import payload_to_source_reference
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


class TestCollectionLifecycle:
    def test_create_collection_exists_and_is_searchable(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        assert not vector_store.collection_exists()
        vector_store.create_collection()
        assert vector_store.collection_exists()

    def test_create_collection_raises_when_already_exists(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        vector_store.create_collection()
        with pytest.raises(CollectionAlreadyExistsError):
            vector_store.create_collection()

    def test_delete_collection_is_idempotent(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        vector_store.create_collection()
        vector_store.delete_collection()
        assert not vector_store.collection_exists()
        vector_store.delete_collection()


class TestUpsertAndSearchDense:
    def test_upsert_and_search_returns_results_ordered_by_score(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        vector_store.create_collection()
        chunk_id_near = str(uuid.uuid4())
        chunk_id_far = str(uuid.uuid4())
        items = (
            _make_item(
                chunk_id=chunk_id_near,
                dense_vector=(1.0, 0.0, 0.0, 0.0),
                text="near match",
            ),
            _make_item(
                chunk_id=chunk_id_far,
                dense_vector=(0.0, 1.0, 0.0, 0.0),
                text="far match",
            ),
        )
        vector_store.upsert_chunks(items)

        results = vector_store.search_dense(
            vector=[1.0, 0.0, 0.0, 0.0],
            top_k=2,
        )

        assert len(results) == 2
        assert results[0].chunk.chunk_id == ChunkId(chunk_id_near)
        assert results[0].chunk.text == "near match"
        assert results[0].score >= results[1].score

    def test_search_returns_empty_tuple_for_empty_collection(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        vector_store.create_collection()
        results = vector_store.search_dense(
            vector=[1.0, 0.0, 0.0, 0.0],
            top_k=5,
        )
        assert results == ()

    def test_search_raises_when_collection_missing(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        with pytest.raises(CollectionNotFoundError):
            vector_store.search_dense(vector=[1.0, 0.0, 0.0, 0.0], top_k=1)

    def test_upsert_raises_when_collection_missing(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        item = _make_item(
            chunk_id=str(uuid.uuid4()),
            dense_vector=(1.0, 0.0, 0.0, 0.0),
            text="text",
        )
        with pytest.raises(CollectionNotFoundError):
            vector_store.upsert_chunks((item,))

    def test_sparse_vectors_are_stored(
        self,
        vector_store: QdrantVectorStore,
        qdrant_client: QdrantClient,
    ) -> None:
        vector_store.create_collection()
        chunk_id = str(uuid.uuid4())
        item = _make_item(
            chunk_id=chunk_id,
            dense_vector=(1.0, 0.0, 0.0, 0.0),
            text="sparse stored",
        )
        vector_store.upsert_chunks((item,))

        retrieved = qdrant_client.retrieve(
            collection_name=vector_store.settings.collection_name,
            ids=[chunk_id],
            with_vectors=True,
        )
        assert retrieved
        vectors = retrieved[0].vector
        assert isinstance(vectors, dict)
        assert DENSE_VECTOR_NAME in vectors
        assert SPARSE_VECTOR_NAME in vectors
        sparse = vectors[SPARSE_VECTOR_NAME]
        assert isinstance(sparse, models.SparseVector)
        assert sparse.indices == [0, 2]
        assert sparse.values == [0.8, 0.2]

    def test_chunk_id_round_trips_through_search(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        vector_store.create_collection()
        chunk_id = str(uuid.uuid4())
        item = _make_item(
            chunk_id=chunk_id,
            dense_vector=(1.0, 0.0, 0.0, 0.0),
            text="identity preserved",
        )
        vector_store.upsert_chunks((item,))

        results = vector_store.search_dense(vector=[1.0, 0.0, 0.0, 0.0], top_k=1)

        assert results[0].chunk.chunk_id == ChunkId(chunk_id)

    def test_non_uuid_chunk_id_rejected_on_upsert(
        self,
        vector_store: QdrantVectorStore,
    ) -> None:
        vector_store.create_collection()
        item = _make_item(
            chunk_id="chunk-123",
            dense_vector=(1.0, 0.0, 0.0, 0.0),
            text="text",
        )
        with pytest.raises(
            InvalidChunkIdError, match="chunk_id must be a valid UUID string"
        ):
            vector_store.upsert_chunks((item,))

    def test_source_reference_round_trip_through_storage(
        self,
        vector_store: QdrantVectorStore,
        qdrant_client: QdrantClient,
    ) -> None:
        vector_store.create_collection()
        chunk_id = str(uuid.uuid4())
        item = _make_item(
            chunk_id=chunk_id,
            dense_vector=(1.0, 0.0, 0.0, 0.0),
            text="source attribution text",
        )
        vector_store.upsert_chunks((item,))

        retrieved = qdrant_client.retrieve(
            collection_name=vector_store.settings.collection_name,
            ids=[chunk_id],
            with_payload=True,
        )
        assert retrieved and retrieved[0].payload is not None

        reference = payload_to_source_reference(retrieved[0].payload)

        assert reference == SourceReference(
            document_title="Guide",
            document_path="docs/guide.md",
            section_title="Overview",
            line_range=LineRange(start_line=1, end_line=5),
        )
