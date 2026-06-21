"""Unit tests for retrieval configuration."""

import pytest

from knowledge_assistant.retrieval.config import DenseRetrievalSettings


class TestDenseRetrievalSettings:
    def test_default_dense_vector_size(self) -> None:
        settings = DenseRetrievalSettings()
        assert settings.dense_vector_size == 1024

    def test_custom_dense_vector_size(self) -> None:
        settings = DenseRetrievalSettings(dense_vector_size=8)
        assert settings.dense_vector_size == 8

    @pytest.mark.parametrize("dense_vector_size", [0, -1])
    def test_dense_vector_size_must_be_positive(self, dense_vector_size: int) -> None:
        with pytest.raises(ValueError, match="dense_vector_size must be > 0"):
            DenseRetrievalSettings(dense_vector_size=dense_vector_size)
