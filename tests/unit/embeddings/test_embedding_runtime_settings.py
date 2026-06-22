"""Unit tests for embedding runtime settings."""

import pytest

from knowledge_assistant.embeddings import EmbeddingRuntimeSettings


class TestEmbeddingRuntimeSettings:
    def test_defaults_are_valid(self) -> None:
        settings = EmbeddingRuntimeSettings(dense_vector_size=1024)

        assert settings.model_name == "BAAI/bge-m3"
        assert settings.device == "cpu"
        assert settings.batch_size == 32
        assert settings.max_length == 8192
        assert settings.normalize_embeddings is True
        assert settings.dense_vector_size == 1024

    @pytest.mark.parametrize(
        ("field_name", "value", "message"),
        [
            ("model_name", "", "model_name must be non-empty"),
            ("batch_size", 0, "batch_size must be > 0"),
            ("max_length", 0, "max_length must be > 0"),
            ("dense_vector_size", 0, "dense_vector_size must be > 0"),
        ],
    )
    def test_rejects_invalid_values(
        self,
        field_name: str,
        value: object,
        message: str,
    ) -> None:
        kwargs = {"dense_vector_size": 1024, field_name: value}
        with pytest.raises(ValueError, match=message):
            EmbeddingRuntimeSettings(**kwargs)  # type: ignore[arg-type]

    def test_rejects_invalid_device(self) -> None:
        with pytest.raises(ValueError, match="device must be one of"):
            EmbeddingRuntimeSettings(device="tpu", dense_vector_size=1024)  # type: ignore[arg-type]
