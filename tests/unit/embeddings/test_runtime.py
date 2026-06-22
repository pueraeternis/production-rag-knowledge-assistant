"""Unit tests for BGE-M3 FlagEmbedding runtime with mocked backend."""

from __future__ import annotations

import math
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from knowledge_assistant.embeddings import (
    BgeM3FlagEmbeddingRuntime,
    EmbeddingDimensionMismatchError,
    EmbeddingRuntimeSettings,
    create_dense_embedding_runtime,
)
from knowledge_assistant.embeddings.exceptions import EmbeddingDeviceError
from knowledge_assistant.embeddings.runtime import (
    l2_normalize,
    validate_device_available,
)


class FakeFlagModel:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.encode_calls: list[dict[str, Any]] = []
        self.encode_queries_calls: list[dict[str, Any]] = []

    def encode(
        self, sentences: list[str], **kwargs: object
    ) -> dict[str, list[list[float]]]:
        self.encode_calls.append({"sentences": sentences, "kwargs": kwargs})
        return {
            "dense_vecs": [[float(index + 1)] * 4 for index, _ in enumerate(sentences)],
        }

    def encode_queries(
        self,
        queries: list[str],
        **kwargs: object,
    ) -> dict[str, list[list[float]]]:
        self.encode_queries_calls.append({"queries": queries, "kwargs": kwargs})
        return {
            "dense_vecs": [[float(index + 10)] * 4 for index, _ in enumerate(queries)],
        }


@pytest.fixture
def runtime_settings() -> EmbeddingRuntimeSettings:
    return EmbeddingRuntimeSettings(
        model_name="BAAI/bge-m3",
        device="cpu",
        batch_size=2,
        max_length=128,
        normalize_embeddings=True,
        dense_vector_size=4,
    )


class TestBgeM3FlagEmbeddingRuntime:
    def test_embed_passages_batches_and_preserves_order(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModel):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            model = cast(FakeFlagModel, runtime._model)  # pyright: ignore[reportPrivateUsage]
            vectors = runtime.embed_passages(("a", "b", "c"))

        assert len(vectors) == 3
        assert model.encode_calls[0]["sentences"] == ["a", "b", "c"]
        encode_kwargs = model.encode_calls[0]["kwargs"]
        assert encode_kwargs["batch_size"] == 2
        assert encode_kwargs["return_dense"] is True
        assert encode_kwargs["return_sparse"] is False

    def test_embed_query_uses_encode_queries(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModel):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            model = cast(FakeFlagModel, runtime._model)  # pyright: ignore[reportPrivateUsage]
            vector = runtime.embed_query("search me")

        assert len(vector) == 4
        assert model.encode_queries_calls[0]["queries"] == ["search me"]
        query_kwargs = model.encode_queries_calls[0]["kwargs"]
        assert "batch_size" not in query_kwargs
        assert query_kwargs["return_dense"] is True
        assert query_kwargs["return_sparse"] is False

    def test_empty_passages_returns_empty_tuple(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModel):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            assert runtime.embed_passages(()) == ()

    def test_outputs_are_l2_normalized(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModel):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            vector = runtime.embed_query("normalize")

        norm = math.sqrt(sum(value * value for value in vector))
        assert math.isclose(norm, 1.0, rel_tol=1e-6)

    def test_dimension_mismatch_raises(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModel):
            runtime = BgeM3FlagEmbeddingRuntime(
                settings=EmbeddingRuntimeSettings(
                    model_name=runtime_settings.model_name,
                    device=runtime_settings.device,
                    batch_size=runtime_settings.batch_size,
                    max_length=runtime_settings.max_length,
                    normalize_embeddings=runtime_settings.normalize_embeddings,
                    dense_vector_size=8,
                ),
            )
            with pytest.raises(EmbeddingDimensionMismatchError, match="expected 8"):
                runtime.embed_query("too short")

    def test_create_dense_embedding_runtime_returns_protocol(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModel):
            runtime = create_dense_embedding_runtime(runtime_settings)

        assert runtime.embed_passages(("x",))[0]


class TestDeviceValidation:
    def test_cpu_requires_no_accelerator(self) -> None:
        validate_device_available("cpu")

    @patch("torch.cuda.is_available", return_value=False)
    def test_cuda_unavailable_raises(self, _cuda: MagicMock) -> None:
        with pytest.raises(EmbeddingDeviceError, match="cuda"):
            validate_device_available("cuda")

    @patch("torch.backends.mps.is_available", return_value=False)
    def test_mps_unavailable_raises(self, _mps: MagicMock) -> None:
        with pytest.raises(EmbeddingDeviceError, match="mps"):
            validate_device_available("mps")


class TestL2Normalize:
    def test_normalizes_non_unit_vector(self) -> None:
        vector = (3.0, 4.0)
        normalized = l2_normalize(vector)
        norm = math.sqrt(sum(value * value for value in normalized))
        assert math.isclose(norm, 1.0, rel_tol=1e-6)
