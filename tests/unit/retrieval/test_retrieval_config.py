"""Unit tests for retrieval configuration."""

import pytest

from knowledge_assistant.retrieval.config import (
    BgeRerankerSettings,
    DenseRetrievalSettings,
    FusionRetrievalSettings,
    parse_reranker_mode,
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


class TestBgeRerankerSettings:
    def test_defaults(self) -> None:
        settings = BgeRerankerSettings()
        assert settings.model_name == "BAAI/bge-reranker-v2-m3"
        assert settings.device == "auto"
        assert settings.batch_size == 16
        assert settings.max_length == 1024
        assert settings.use_fp16 is False

    @pytest.mark.parametrize("model_name", ["", "   "])
    def test_model_name_must_be_non_empty(self, model_name: str) -> None:
        with pytest.raises(ValueError, match="model_name must be non-empty"):
            BgeRerankerSettings(model_name=model_name)

    @pytest.mark.parametrize("device", ["auto", "cpu", "cuda", "cuda:0", "cuda:12"])
    def test_supported_devices(self, device: str) -> None:
        assert BgeRerankerSettings(device=device).device == device

    @pytest.mark.parametrize("device", ["gpu", "cuda:", "cuda:x", "mps"])
    def test_rejects_unsupported_devices(self, device: str) -> None:
        with pytest.raises(ValueError, match="device must be"):
            BgeRerankerSettings(device=device)

    @pytest.mark.parametrize("batch_size", [0, -1])
    def test_batch_size_must_be_at_least_one(self, batch_size: int) -> None:
        with pytest.raises(ValueError, match="batch_size must be >= 1"):
            BgeRerankerSettings(batch_size=batch_size)

    @pytest.mark.parametrize("max_length", [0, -1])
    def test_max_length_must_be_at_least_one(self, max_length: int) -> None:
        with pytest.raises(ValueError, match="max_length must be >= 1"):
            BgeRerankerSettings(max_length=max_length)

    def test_cpu_rejects_fp16(self) -> None:
        with pytest.raises(ValueError, match="use_fp16 must be false"):
            BgeRerankerSettings(device="cpu", use_fp16=True)

    def test_from_env_reads_reranker_variables(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RAG_RERANKER_MODEL", "custom/model")
        monkeypatch.setenv("RAG_RERANKER_DEVICE", "cuda:0")
        monkeypatch.setenv("RAG_RERANKER_BATCH_SIZE", "8")
        monkeypatch.setenv("RAG_RERANKER_MAX_LENGTH", "256")
        monkeypatch.setenv("RAG_RERANKER_USE_FP16", "true")

        settings = BgeRerankerSettings.from_env()

        assert settings == BgeRerankerSettings(
            model_name="custom/model",
            device="cuda:0",
            batch_size=8,
            max_length=256,
            use_fp16=True,
        )

    def test_from_env_allows_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RAG_RERANKER_MODEL", "env/model")

        settings = BgeRerankerSettings.from_env(model_name="override/model")

        assert settings.model_name == "override/model"


class TestParseRerankerMode:
    @pytest.mark.parametrize("value", [None, "", "stub", " STUB "])
    def test_stub_mode(self, value: str | None) -> None:
        assert parse_reranker_mode(value) == "stub"

    @pytest.mark.parametrize("value", ["real", " REAL "])
    def test_real_mode(self, value: str) -> None:
        assert parse_reranker_mode(value) == "real"

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="reranker mode must be"):
            parse_reranker_mode("auto")
