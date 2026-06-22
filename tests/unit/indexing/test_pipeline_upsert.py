"""Unit tests for indexing pipeline upsert assembly."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from knowledge_assistant.core import indexing as core_indexing
from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.embeddings import (
    StubEmbeddingProvider,
    StubSparseEmbeddingProvider,
)
from knowledge_assistant.indexing.pipeline import IndexingPipeline
from knowledge_assistant.storage.models import ChunkUpsertItem, SparseVector

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestIndexingPipelineUpsertAssembly:
    @pytest.fixture
    def settings(self) -> IndexingSettings:
        return IndexingSettings(chunk_size=1024, chunk_overlap=0, dense_vector_size=8)

    @pytest.fixture
    def source(self) -> core_indexing.IndexingSource:
        return core_indexing.IndexingSource(
            kind=core_indexing.IndexingSourceKind.FILE,
            location=str(FIXTURES_DIR / "sample.txt"),
            recursive=False,
        )

    def test_builds_chunk_upsert_items_with_vectors(
        self,
        settings: IndexingSettings,
        source: core_indexing.IndexingSource,
    ) -> None:
        vector_store = MagicMock()
        vector_store.collection_exists.return_value = False
        captured_items: list[tuple[ChunkUpsertItem, ...]] = []

        def capture_upsert(items: tuple[ChunkUpsertItem, ...]) -> None:
            captured_items.append(items)

        vector_store.upsert_chunks.side_effect = capture_upsert

        pipeline = IndexingPipeline(
            vector_store=vector_store,
            embedding_provider=StubEmbeddingProvider(dimension=8),
            sparse_embedding_provider=StubSparseEmbeddingProvider(),
            settings=settings,
        )
        result = pipeline.index_documents((source,))

        assert result.upserted_count == 1
        assert len(captured_items) == 1
        item = captured_items[0][0]
        assert item.document_metadata.title == "sample"
        assert len(item.dense_vector) == 8
        assert item.sparse_vector.indices
        assert item.sparse_vector != SparseVector(indices=(0,), values=(1.0,))
