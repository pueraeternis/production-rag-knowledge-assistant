"""Indexing pipeline orchestration."""

from dataclasses import dataclass

from knowledge_assistant.core.chunk import Chunk
from knowledge_assistant.core.document import DocumentMetadata
from knowledge_assistant.core.indexing import IndexingPreview, IndexingSource
from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.documents import discover_files
from knowledge_assistant.indexing.embeddings import (
    EmbeddingProvider,
    SparseEmbeddingProvider,
)
from knowledge_assistant.indexing.exceptions import EmbeddingDimensionError
from knowledge_assistant.indexing.ids import document_id_for_path
from knowledge_assistant.indexing.llamaindex_adapter import load_and_chunk_file
from knowledge_assistant.storage.models import ChunkUpsertItem
from knowledge_assistant.storage.protocol import VectorStore


@dataclass(frozen=True, slots=True)
class IndexingResult:
    """Summary returned after a successful index run."""

    sources: tuple[IndexingSource, ...]
    document_count: int
    chunk_count: int
    upserted_count: int
    rebuilt: bool


class IndexingPipeline:
    """Load, chunk, embed, and upsert local documents into a vector store."""

    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        sparse_embedding_provider: SparseEmbeddingProvider,
        settings: IndexingSettings,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._sparse_embedding_provider = sparse_embedding_provider
        self._settings = settings

    def preview_indexing(
        self,
        sources: tuple[IndexingSource, ...],
    ) -> IndexingPreview:
        document_count = 0
        chunk_count = 0
        for file_path in self._discover_all_files(sources):
            document_id = document_id_for_path(file_path)
            _, chunks = load_and_chunk_file(
                file_path=file_path,
                document_id=document_id,
                settings=self._settings,
            )
            document_count += 1
            chunk_count += len(chunks)

        return IndexingPreview(
            sources=sources,
            document_count=document_count,
            chunk_count=chunk_count,
            replaces_existing=self._vector_store.collection_exists(),
        )

    def index_documents(
        self,
        sources: tuple[IndexingSource, ...],
        *,
        rebuild: bool = False,
    ) -> IndexingResult:
        file_paths = self._discover_all_files(sources)
        if not file_paths:
            return IndexingResult(
                sources=sources,
                document_count=0,
                chunk_count=0,
                upserted_count=0,
                rebuilt=False,
            )

        loaded_documents: list[tuple[str, DocumentMetadata, tuple[Chunk, ...]]] = []
        for file_path in file_paths:
            document_id = document_id_for_path(file_path)
            metadata, chunks = load_and_chunk_file(
                file_path=file_path,
                document_id=document_id,
                settings=self._settings,
            )
            loaded_documents.append((file_path, metadata, chunks))

        chunk_texts = tuple(
            chunk.text for _, _, chunks in loaded_documents for chunk in chunks
        )
        if not chunk_texts:
            return IndexingResult(
                sources=sources,
                document_count=len(loaded_documents),
                chunk_count=0,
                upserted_count=0,
                rebuilt=False,
            )

        dense_vectors = self._embedding_provider.embed_texts(chunk_texts)
        sparse_vectors = self._sparse_embedding_provider.embed_sparse_texts(chunk_texts)

        upsert_items: list[ChunkUpsertItem] = []
        vector_index = 0
        for _, metadata, chunks in loaded_documents:
            for chunk in chunks:
                dense_vector = dense_vectors[vector_index]
                sparse_vector = sparse_vectors[vector_index]
                vector_index += 1
                self._validate_dense_vector(dense_vector)
                upsert_items.append(
                    ChunkUpsertItem(
                        chunk=chunk,
                        document_metadata=metadata,
                        dense_vector=dense_vector,
                        sparse_vector=sparse_vector,
                    ),
                )

        if rebuild:
            self._vector_store.delete_collection()
            self._vector_store.create_collection()
        elif not self._vector_store.collection_exists():
            self._vector_store.create_collection()

        items = tuple(upsert_items)
        self._vector_store.upsert_chunks(items)

        document_count = len(loaded_documents)
        chunk_count = len(items)
        return IndexingResult(
            sources=sources,
            document_count=document_count,
            chunk_count=chunk_count,
            upserted_count=chunk_count,
            rebuilt=rebuild,
        )

    def _discover_all_files(
        self,
        sources: tuple[IndexingSource, ...],
    ) -> tuple[str, ...]:
        discovered: list[str] = []
        for source in sources:
            discovered.extend(
                discover_files(source, settings=self._settings),
            )
        return tuple(discovered)

    def _validate_dense_vector(self, dense_vector: tuple[float, ...]) -> None:
        if len(dense_vector) != self._settings.dense_vector_size:
            msg = (
                "embedding dimension "
                f"{len(dense_vector)} does not match "
                f"expected {self._settings.dense_vector_size}"
            )
            raise EmbeddingDimensionError(msg)
