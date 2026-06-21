"""Unit tests for retrieval configuration."""

import pytest

from knowledge_assistant.retrieval.config import (
    DenseRetrievalSettings,
    FusionRetrievalSettings,
)


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


class TestFusionRetrievalSettings:
    def test_defaults(self) -> None:
        settings = FusionRetrievalSettings()
        assert settings.rrf_k == 60
        assert settings.leaf_top_k_multiplier == 2

    def test_resolve_leaf_top_k(self) -> None:
        settings = FusionRetrievalSettings(leaf_top_k_multiplier=2)
        assert settings.resolve_leaf_top_k(5) == 10

    @pytest.mark.parametrize("rrf_k", [0, -1])
    def test_rrf_k_must_be_at_least_one(self, rrf_k: int) -> None:
        with pytest.raises(ValueError, match="rrf_k must be >= 1"):
            FusionRetrievalSettings(rrf_k=rrf_k)

    @pytest.mark.parametrize("leaf_top_k_multiplier", [0, -1])
    def test_leaf_top_k_multiplier_must_be_at_least_one(
        self,
        leaf_top_k_multiplier: int,
    ) -> None:
        with pytest.raises(ValueError, match="leaf_top_k_multiplier must be >= 1"):
            FusionRetrievalSettings(leaf_top_k_multiplier=leaf_top_k_multiplier)
