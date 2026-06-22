"""Integration tests for stub sparse vectors in the indexing pipeline."""

from pathlib import Path

from conftest import FakeVectorStore

from knowledge_assistant.core.indexing import IndexingSource, IndexingSourceKind
from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.embeddings import (
    StubEmbeddingProvider,
    StubSparseEmbeddingProvider,
)
from knowledge_assistant.indexing.pipeline import IndexingPipeline

FIXTURES_DIR = Path(__file__).parents[2] / "unit" / "indexing" / "fixtures"


def test_stub_sparse_provider_produces_per_chunk_vectors(
    fake_vector_store: FakeVectorStore,
) -> None:
    settings = IndexingSettings(chunk_size=64, chunk_overlap=0, dense_vector_size=8)
    source = IndexingSource(
        kind=IndexingSourceKind.FILE,
        location=str(FIXTURES_DIR / "sample.txt"),
        recursive=False,
    )
    pipeline = IndexingPipeline(
        vector_store=fake_vector_store,
        embedding_provider=StubEmbeddingProvider(dimension=8),
        sparse_embedding_provider=StubSparseEmbeddingProvider(),
        settings=settings,
    )

    pipeline.index_documents((source,))

    assert len(fake_vector_store.upserted_items) >= 1
    for item in fake_vector_store.upserted_items:
        assert item.sparse_vector.indices
        assert item.sparse_vector.indices != (0,)
