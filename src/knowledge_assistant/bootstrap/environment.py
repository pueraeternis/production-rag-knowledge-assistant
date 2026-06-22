"""Demo environment assembly for storage, indexing, and retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from knowledge_assistant.bootstrap.config import (
    STUB_PIPELINE_LABEL,
    BootstrapSettings,
    retrieval_pipeline_label,
)
from knowledge_assistant.bootstrap.retrievers import (
    RetrievalStack,
    build_retrieval_stack,
)
from knowledge_assistant.core import IndexingSource, IndexingSourceKind
from knowledge_assistant.embeddings import (
    DenseEmbeddingRuntime,
    create_shared_dense_embedding_runtime,
)
from knowledge_assistant.indexing import (
    BgeM3EmbeddingProvider,
    IndexingPipeline,
    StubEmbeddingProvider,
)
from knowledge_assistant.indexing.documents import discover_files
from knowledge_assistant.retrieval import (
    BgeM3QueryEmbeddingProvider,
    BgeReranker,
    RerankRetriever,
    StubQueryEmbeddingProvider,
    StubReranker,
)
from knowledge_assistant.storage import VectorStore, create_qdrant_vector_store

DEMO_RETRIEVAL_PIPELINE_LABEL = STUB_PIPELINE_LABEL


@dataclass(frozen=True, slots=True)
class DemoEnvironment:
    """Assembled demo stack with read-only status helpers."""

    settings: BootstrapSettings
    vector_store: VectorStore
    indexing_pipeline: IndexingPipeline
    retriever: RerankRetriever
    reranker: StubReranker | BgeReranker
    retrieval_stack: RetrievalStack

    @property
    def pipeline_label(self) -> str:
        return self.settings.pipeline_label

    @property
    def retrieval_pipeline_label(self) -> str:
        return self.pipeline_label

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


def _build_dense_embedding_runtime(
    settings: BootstrapSettings,
) -> DenseEmbeddingRuntime:
    assert settings.embedding_runtime_settings is not None
    return create_shared_dense_embedding_runtime(settings.embedding_runtime_settings)


def build_demo_environment(
    *,
    settings: BootstrapSettings | None = None,
    vector_store: VectorStore | None = None,
) -> DemoEnvironment:
    """Assemble the canonical demo stack with stub or real dense embedding providers."""
    resolved_settings = settings or BootstrapSettings.from_env()
    resolved_store = vector_store or create_qdrant_vector_store(
        resolved_settings.storage_settings,
    )

    if resolved_settings.embedding_mode == "real":
        runtime = _build_dense_embedding_runtime(resolved_settings)
        embedding_provider = BgeM3EmbeddingProvider(runtime=runtime)
        query_embedding_provider = BgeM3QueryEmbeddingProvider(runtime=runtime)
    else:
        embedding_provider = StubEmbeddingProvider(
            dimension=resolved_settings.dense_vector_size,
        )
        query_embedding_provider = StubQueryEmbeddingProvider(
            dimension=resolved_settings.dense_vector_size,
        )

    indexing_pipeline = IndexingPipeline(
        vector_store=resolved_store,
        embedding_provider=embedding_provider,
        settings=resolved_settings.indexing_settings,
    )

    retrieval_stack = build_retrieval_stack(
        settings=resolved_settings,
        vector_store=resolved_store,
        query_embedding_provider=query_embedding_provider,
    )

    return DemoEnvironment(
        settings=resolved_settings,
        vector_store=resolved_store,
        indexing_pipeline=indexing_pipeline,
        retriever=retrieval_stack.rerank_retriever,
        reranker=retrieval_stack.reranker,
        retrieval_stack=retrieval_stack,
    )


__all__ = (
    "DEMO_RETRIEVAL_PIPELINE_LABEL",
    "DemoEnvironment",
    "build_demo_environment",
    "retrieval_pipeline_label",
)
