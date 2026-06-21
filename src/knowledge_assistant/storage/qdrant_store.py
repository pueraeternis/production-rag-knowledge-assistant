"""Qdrant-backed VectorStore implementation."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from qdrant_client import QdrantClient, models

from knowledge_assistant.core.identifiers import ChunkId
from knowledge_assistant.core.retrieval import SearchResult
from knowledge_assistant.storage.collection import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.exceptions import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    InvalidChunkIdError,
    VectorDimensionError,
)
from knowledge_assistant.storage.mapping import (
    chunk_upsert_item_to_payload,
    payload_to_chunk,
)
from knowledge_assistant.storage.models import ChunkUpsertItem
from knowledge_assistant.storage.validation import validate_sparse_search_input


def _chunk_id_to_point_id(chunk_id: ChunkId) -> str:
    value = str(chunk_id)
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        msg = f"chunk_id must be a valid UUID string: {value!r}"
        raise InvalidChunkIdError(msg) from exc
    return str(parsed)


def _point_id_to_chunk_id(point_id: object) -> ChunkId:
    return ChunkId(str(point_id))


class QdrantVectorStore:
    """Concrete VectorStore backed by a Qdrant collection."""

    def __init__(self, *, client: QdrantClient, settings: StorageSettings) -> None:
        self._client = client
        self._settings = settings

    @property
    def settings(self) -> StorageSettings:
        return self._settings

    def create_collection(self) -> None:
        if self.collection_exists():
            msg = f"collection {self._settings.collection_name!r} already exists"
            raise CollectionAlreadyExistsError(msg)
        self._client.create_collection(
            collection_name=self._settings.collection_name,
            vectors_config={
                DENSE_VECTOR_NAME: models.VectorParams(
                    size=self._settings.dense_vector_size,
                    distance=models.Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: models.SparseVectorParams(),
            },
        )

    def delete_collection(self) -> None:
        if not self.collection_exists():
            return
        self._client.delete_collection(collection_name=self._settings.collection_name)

    def collection_exists(self) -> bool:
        return self._client.collection_exists(
            collection_name=self._settings.collection_name,
        )

    def upsert_chunks(self, items: tuple[ChunkUpsertItem, ...]) -> None:
        if not self.collection_exists():
            msg = f"collection {self._settings.collection_name!r} not found"
            raise CollectionNotFoundError(msg)
        if not items:
            return

        points: list[models.PointStruct] = []
        for item in items:
            self._validate_dense_vector(item.dense_vector)
            points.append(
                models.PointStruct(
                    id=_chunk_id_to_point_id(item.chunk.chunk_id),
                    vector={
                        DENSE_VECTOR_NAME: list(item.dense_vector),
                        SPARSE_VECTOR_NAME: models.SparseVector(
                            indices=list(item.sparse_vector.indices),
                            values=list(item.sparse_vector.values),
                        ),
                    },
                    payload=chunk_upsert_item_to_payload(item),
                ),
            )
        self._client.upsert(
            collection_name=self._settings.collection_name,
            points=points,
        )

    def search_dense(
        self,
        *,
        vector: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        if not self.collection_exists():
            msg = f"collection {self._settings.collection_name!r} not found"
            raise CollectionNotFoundError(msg)
        if top_k < 1:
            msg = "top_k must be >= 1"
            raise ValueError(msg)

        self._validate_dense_vector(vector)
        response = self._client.query_points(
            collection_name=self._settings.collection_name,
            query=list(vector),
            using=DENSE_VECTOR_NAME,
            limit=top_k,
        )
        results: list[SearchResult] = []
        for point in response.points:
            if point.payload is None:
                continue
            chunk_id = _point_id_to_chunk_id(point.id)
            chunk = payload_to_chunk(point.payload, chunk_id=chunk_id)
            results.append(SearchResult(chunk=chunk, score=point.score))
        return tuple(results)

    def search_sparse(
        self,
        *,
        indices: Sequence[int],
        values: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        if not self.collection_exists():
            msg = f"collection {self._settings.collection_name!r} not found"
            raise CollectionNotFoundError(msg)
        if top_k < 1:
            msg = "top_k must be >= 1"
            raise ValueError(msg)
        if len(indices) == 0:
            return ()

        validate_sparse_search_input(indices, values)
        response = self._client.query_points(
            collection_name=self._settings.collection_name,
            query=models.SparseVector(indices=list(indices), values=list(values)),
            using=SPARSE_VECTOR_NAME,
            limit=top_k,
        )
        results: list[SearchResult] = []
        for point in response.points:
            if point.payload is None:
                continue
            chunk_id = _point_id_to_chunk_id(point.id)
            chunk = payload_to_chunk(point.payload, chunk_id=chunk_id)
            results.append(SearchResult(chunk=chunk, score=point.score))
        return tuple(results)

    def _validate_dense_vector(self, vector: Sequence[float]) -> None:
        expected = self._settings.dense_vector_size
        actual = len(vector)
        if actual != expected:
            msg = f"dense vector dimension mismatch: expected {expected}, got {actual}"
            raise VectorDimensionError(msg)


def create_qdrant_vector_store(
    settings: StorageSettings,
    *,
    client: QdrantClient | None = None,
) -> QdrantVectorStore:
    """Create a Qdrant-backed vector store from settings."""
    resolved_client = (
        client if client is not None else QdrantClient(url=settings.qdrant_url)
    )
    return QdrantVectorStore(client=resolved_client, settings=settings)
