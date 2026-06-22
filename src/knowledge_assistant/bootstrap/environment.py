"""Demo environment assembly for storage, indexing, and retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from knowledge_assistant.bootstrap.config import BootstrapSettings
from knowledge_assistant.core import IndexingSource, IndexingSourceKind
from knowledge_assistant.indexing import IndexingPipeline, StubEmbeddingProvider
from knowledge_assistant.indexing.documents import discover_files
from knowledge_assistant.retrieval import (
    DenseRetriever,
    FusionRetrievalSettings,
    FusionRetriever,
    RerankRetrievalSettings,
    RerankRetriever,
    SparseRetriever,
    StubQueryEmbeddingProvider,
    StubReranker,
    StubSparseQueryEmbeddingProvider,
)
from knowledge_assistant.storage import VectorStore, create_qdrant_vector_store

DEMO_RETRIEVAL_PIPELINE_LABEL = "dense + sparse → fusion (RRF) → rerank (stub)"


@dataclass(frozen=True, slots=True)
class DemoEnvironment:
    """Assembled demo stack with read-only status helpers."""

    settings: BootstrapSettings
    vector_store: VectorStore
    indexing_pipeline: IndexingPipeline
    retriever: RerankRetriever

    def corpus_exists(self) -> bool:
        return self.settings.corpus_root.is_dir()

    def corpus_document_count(self) -> int:
        if not self.corpus_exists():
            return 0
        source = IndexingSource(
            kind=IndexingSourceKind.DIRECTORY,
            location=str(self.settings.corpus_root.resolve()),
            recursive=True,
        )
        discovered = discover_files(
            source,
            settings=self.settings.indexing_settings,
        )
        return len(discovered)

    def collection_exists(self) -> bool:
        return self.vector_store.collection_exists()

    def collection_chunk_count(self) -> int:
        return self.vector_store.count_points()

    def corpus_indexing_source(self) -> IndexingSource:
        return IndexingSource(
            kind=IndexingSourceKind.DIRECTORY,
            location=str(self.settings.corpus_root.resolve()),
            recursive=True,
        )


def build_demo_environment(
    *,
    settings: BootstrapSettings | None = None,
    vector_store: VectorStore | None = None,
) -> DemoEnvironment:
    """Assemble the canonical demo stack using stub providers."""
    resolved_settings = settings or BootstrapSettings.from_env()
    resolved_store = vector_store or create_qdrant_vector_store(
        resolved_settings.storage_settings,
    )

    indexing_pipeline = IndexingPipeline(
        vector_store=resolved_store,
        embedding_provider=StubEmbeddingProvider(
            dimension=resolved_settings.dense_vector_size,
        ),
        settings=resolved_settings.indexing_settings,
    )

    dense_retriever = DenseRetriever(
        vector_store=resolved_store,
        embedding_provider=StubQueryEmbeddingProvider(
            dimension=resolved_settings.dense_vector_size,
        ),
        settings=resolved_settings.dense_retrieval_settings,
    )
    sparse_retriever = SparseRetriever(
        vector_store=resolved_store,
        embedding_provider=StubSparseQueryEmbeddingProvider(),
    )
    fusion_retriever = FusionRetriever(
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever,
        settings=FusionRetrievalSettings(),
    )
    retriever = RerankRetriever(
        base_retriever=fusion_retriever,
        reranker=StubReranker(),
        settings=RerankRetrievalSettings(),
    )

    return DemoEnvironment(
        settings=resolved_settings,
        vector_store=resolved_store,
        indexing_pipeline=indexing_pipeline,
        retriever=retriever,
    )
