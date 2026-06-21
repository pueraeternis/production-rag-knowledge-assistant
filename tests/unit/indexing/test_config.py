"""Unit tests for IndexingSettings validation."""

import pytest

from knowledge_assistant.indexing.config import IndexingSettings


class TestIndexingSettings:
    def test_defaults(self) -> None:
        settings = IndexingSettings()

        assert settings.chunk_size == 1024
        assert settings.chunk_overlap == 128
        assert settings.dense_vector_size == 1024
        assert settings.supported_extensions == (".md", ".txt")

    @pytest.mark.parametrize(
        ("chunk_size", "chunk_overlap", "match"),
        [
            (0, 0, "chunk_size must be > 0"),
            (100, -1, "chunk_overlap must be >= 0"),
            (100, 100, "chunk_overlap must be < chunk_size"),
        ],
    )
    def test_rejects_invalid_chunk_configuration(
        self,
        chunk_size: int,
        chunk_overlap: int,
        match: str,
    ) -> None:
        with pytest.raises(ValueError, match=match):
            IndexingSettings(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def test_rejects_non_positive_dense_vector_size(self) -> None:
        with pytest.raises(ValueError, match="dense_vector_size must be > 0"):
            IndexingSettings(dense_vector_size=0)
