"""Integration tests for IndexingPipeline orchestration."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from conftest import FakeVectorStore

from knowledge_assistant.core.indexing import IndexingSource, IndexingSourceKind
from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.embeddings import StubEmbeddingProvider
from knowledge_assistant.indexing.pipeline import IndexingPipeline

FIXTURES_DIR = Path(__file__).parents[2] / "unit" / "indexing" / "fixtures"


class TestIndexingPipelineIntegration:
    @pytest.fixture
    def settings(self) -> IndexingSettings:
        return IndexingSettings(chunk_size=1024, chunk_overlap=0, dense_vector_size=8)

    @pytest.fixture
    def source(self) -> IndexingSource:
        return IndexingSource(
            kind=IndexingSourceKind.FILE,
            location=str(FIXTURES_DIR / "sample.txt"),
            recursive=False,
        )

    @pytest.fixture
    def pipeline(
        self,
        fake_vector_store: FakeVectorStore,
        settings: IndexingSettings,
    ) -> IndexingPipeline:
        return IndexingPipeline(
            vector_store=fake_vector_store,
            embedding_provider=StubEmbeddingProvider(dimension=8),
            settings=settings,
        )

    def test_index_upserts_expected_item_count(
        self,
        pipeline: IndexingPipeline,
        fake_vector_store: FakeVectorStore,
        source: IndexingSource,
    ) -> None:
        result = pipeline.index_documents((source,))

        assert result.upserted_count == 1
        assert len(fake_vector_store.upserted_items) == 1

    def test_index_into_empty_store_creates_collection_then_upserts(
        self,
        pipeline: IndexingPipeline,
        fake_vector_store: FakeVectorStore,
        source: IndexingSource,
    ) -> None:
        pipeline.index_documents((source,))

        assert "create_collection" in fake_vector_store.calls
        assert "upsert_chunks" in fake_vector_store.calls
        assert fake_vector_store.calls.index(
            "create_collection",
        ) < fake_vector_store.calls.index(
            "upsert_chunks",
        )

    def test_rebuild_calls_delete_create_upsert_in_order(
        self,
        pipeline: IndexingPipeline,
        fake_vector_store: FakeVectorStore,
        source: IndexingSource,
    ) -> None:
        fake_vector_store.collection_exists_value = True

        pipeline.index_documents((source,), rebuild=True)

        assert fake_vector_store.calls[:3] == [
            "delete_collection",
            "create_collection",
            "upsert_chunks",
        ]

    def test_reindexing_same_content_produces_identical_chunk_ids(
        self,
        settings: IndexingSettings,
        source: IndexingSource,
    ) -> None:
        first_store = FakeVectorStore(collection_exists=False)
        second_store = FakeVectorStore(collection_exists=False)
        first_pipeline = IndexingPipeline(
            vector_store=first_store,
            embedding_provider=StubEmbeddingProvider(dimension=8),
            settings=settings,
        )
        second_pipeline = IndexingPipeline(
            vector_store=second_store,
            embedding_provider=StubEmbeddingProvider(dimension=8),
            settings=settings,
        )

        first_pipeline.index_documents((source,))
        second_pipeline.index_documents((source,))

        first_ids = [item.chunk.chunk_id for item in first_store.upserted_items]
        second_ids = [item.chunk.chunk_id for item in second_store.upserted_items]
        assert first_ids == second_ids

    def test_preview_does_not_write_to_storage(
        self,
        pipeline: IndexingPipeline,
        fake_vector_store: FakeVectorStore,
        source: IndexingSource,
    ) -> None:
        preview = pipeline.preview_indexing((source,))

        assert preview.document_count == 1
        assert preview.chunk_count == 1
        assert fake_vector_store.calls == ["collection_exists"]
        assert fake_vector_store.upserted_items == ()

    def test_preview_does_not_invoke_embedding_provider(
        self,
        fake_vector_store: FakeVectorStore,
        settings: IndexingSettings,
        source: IndexingSource,
    ) -> None:
        embedding_provider = MagicMock()
        pipeline = IndexingPipeline(
            vector_store=fake_vector_store,
            embedding_provider=embedding_provider,
            settings=settings,
        )

        pipeline.preview_indexing((source,))

        embedding_provider.embed_texts.assert_not_called()

    def test_preview_sets_replaces_existing_from_collection_exists(
        self,
        source: IndexingSource,
        settings: IndexingSettings,
    ) -> None:
        existing_store = FakeVectorStore(collection_exists=True)
        pipeline = IndexingPipeline(
            vector_store=existing_store,
            embedding_provider=StubEmbeddingProvider(dimension=8),
            settings=settings,
        )

        preview = pipeline.preview_indexing((source,))

        assert preview.replaces_existing is True

    def test_preview_empty_directory_returns_zero_counts(
        self,
        pipeline: IndexingPipeline,
        fake_vector_store: FakeVectorStore,
        tmp_path: Path,
    ) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        source = IndexingSource(
            kind=IndexingSourceKind.DIRECTORY,
            location=str(empty_dir),
            recursive=True,
        )

        preview = pipeline.preview_indexing((source,))

        assert preview.document_count == 0
        assert preview.chunk_count == 0
        assert fake_vector_store.calls == ["collection_exists"]

    def test_index_empty_directory_is_storage_no_op(
        self,
        pipeline: IndexingPipeline,
        fake_vector_store: FakeVectorStore,
        tmp_path: Path,
    ) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        source = IndexingSource(
            kind=IndexingSourceKind.DIRECTORY,
            location=str(empty_dir),
            recursive=True,
        )

        result = pipeline.index_documents((source,))

        assert result.document_count == 0
        assert result.chunk_count == 0
        assert result.upserted_count == 0
        assert result.rebuilt is False
        assert fake_vector_store.calls == []

    def test_index_empty_directory_with_rebuild_is_storage_no_op(
        self,
        fake_vector_store: FakeVectorStore,
        settings: IndexingSettings,
        tmp_path: Path,
    ) -> None:
        fake_vector_store.collection_exists_value = True
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        source = IndexingSource(
            kind=IndexingSourceKind.DIRECTORY,
            location=str(empty_dir),
            recursive=True,
        )
        pipeline = IndexingPipeline(
            vector_store=fake_vector_store,
            embedding_provider=StubEmbeddingProvider(dimension=8),
            settings=settings,
        )

        result = pipeline.index_documents((source,), rebuild=True)

        assert result.rebuilt is False
        assert fake_vector_store.calls == []
