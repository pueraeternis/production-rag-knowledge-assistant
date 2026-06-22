"""Unit tests for BGE-M3 FlagEmbedding runtime with mocked backend."""

from __future__ import annotations

import math
from typing import Any, cast
from unittest.mock import patch

import numpy as np
import pytest

from knowledge_assistant.embeddings import (
    BgeM3FlagEmbeddingRuntime,
    EmbeddingDimensionMismatchError,
    EmbeddingRuntimeSettings,
    create_dense_embedding_runtime,
)
from knowledge_assistant.embeddings.exceptions import (
    EmbeddingDeviceError,
    EmbeddingRuntimeError,
)
from knowledge_assistant.embeddings.runtime import (
    l2_normalize,
    validate_device_available,
)


class FakeFlagModel:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.encode_calls: list[dict[str, Any]] = []
        self.encode_queries_calls: list[dict[str, Any]] = []

    def encode(
        self,
        sentences: list[str],
        **kwargs: object,
    ) -> dict[str, list[list[float]] | list[dict[int, float]]]:
        self.encode_calls.append({"sentences": sentences, "kwargs": kwargs})
        return {
            "dense_vecs": [[float(index + 1)] * 4 for index, _ in enumerate(sentences)],
            "lexical_weights": [
                {10 + index: 0.5 + index, 20 + index: 0.25}
                for index, _ in enumerate(sentences)
            ],
        }

    def encode_queries(
        self,
        queries: list[str],
        **kwargs: object,
    ) -> dict[str, list[list[float]] | list[dict[int, float]]]:
        self.encode_queries_calls.append({"queries": queries, "kwargs": kwargs})
        return {
            "dense_vecs": [[float(index + 10)] * 4 for index, _ in enumerate(queries)],
            "lexical_weights": [{100 + index: 0.7} for index, _ in enumerate(queries)],
        }


class FakeFlagModelNumpy:
    """Simulates FlagEmbedding CUDA output: float16 ndarray (batch, dimension)."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def encode(self, sentences: list[str], **_kwargs: object) -> dict[str, np.ndarray]:
        rows = np.array(
            [[float(index + 1)] * 4 for index, _ in enumerate(sentences)],
            dtype=np.float16,
        )
        return {"dense_vecs": rows}

    def encode_queries(
        self,
        queries: list[str],
        **_kwargs: object,
    ) -> dict[str, np.ndarray]:
        rows = np.array(
            [[float(index + 10)] * 4 for index, _ in enumerate(queries)],
            dtype=np.float16,
        )
        return {"dense_vecs": rows}


class FakeFlagModelInvalidNumpy:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def encode(self, _sentences: list[str], **_kwargs: object) -> dict[str, np.ndarray]:
        return {"dense_vecs": np.zeros((2, 3, 4))}

    def encode_queries(
        self,
        _queries: list[str],
        **_kwargs: object,
    ) -> dict[str, np.ndarray]:
        return {"dense_vecs": np.zeros((2, 3, 4))}


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
            model = cast("FakeFlagModel", runtime._model)  # pyright: ignore[reportPrivateUsage]
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
            model = cast("FakeFlagModel", runtime._model)  # pyright: ignore[reportPrivateUsage]
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

    def test_embed_passages_accepts_numpy_ndarray_dense_vecs(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModelNumpy):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            vectors = runtime.embed_passages(("a", "b"))

        assert len(vectors) == 2
        assert all(len(vector) == 4 for vector in vectors)

    def test_embed_query_accepts_numpy_ndarray_dense_vecs(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModelNumpy):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            vector = runtime.embed_query("search me")

        assert len(vector) == 4

    def test_rejects_unsupported_ndarray_rank(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModelInvalidNumpy):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            with pytest.raises(TypeError, match="unsupported dense_vecs shape"):
                runtime.embed_passages(("a",))


class TestBgeM3SparseRuntime:
    def test_embed_passages_sparse_uses_encode_with_sparse(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModel):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            model = cast("FakeFlagModel", runtime._model)  # pyright: ignore[reportPrivateUsage]
            payloads = runtime.embed_passages_sparse(("chunk-a", "chunk-b"))

        assert len(payloads) == 2
        assert payloads[0] == ((10, 20), (0.5, 0.25))
        encode_kwargs = model.encode_calls[0]["kwargs"]
        assert encode_kwargs["return_dense"] is False
        assert encode_kwargs["return_sparse"] is True
        assert encode_kwargs["return_colbert_vecs"] is False

    def test_embed_query_sparse_uses_encode_queries(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModel):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            model = cast("FakeFlagModel", runtime._model)  # pyright: ignore[reportPrivateUsage]
            indices, values = runtime.embed_query_sparse("search me")

        assert indices == (100,)
        assert values == (0.7,)
        query_kwargs = model.encode_queries_calls[0]["kwargs"]
        assert query_kwargs["return_dense"] is False
        assert query_kwargs["return_sparse"] is True
        assert query_kwargs["return_colbert_vecs"] is False

    def test_embed_passages_dual_returns_dense_and_sparse(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        with patch("FlagEmbedding.BGEM3FlagModel", FakeFlagModel):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            model = cast("FakeFlagModel", runtime._model)  # pyright: ignore[reportPrivateUsage]
            dense_vectors, sparse_vectors = runtime.embed_passages_dual(("chunk-a",))

        assert len(dense_vectors) == 1
        assert len(sparse_vectors) == 1
        encode_kwargs = model.encode_calls[0]["kwargs"]
        assert encode_kwargs["return_dense"] is True
        assert encode_kwargs["return_sparse"] is True
        assert encode_kwargs["return_colbert_vecs"] is False

    def test_empty_sparse_weights_raise(
        self,
        runtime_settings: EmbeddingRuntimeSettings,
    ) -> None:
        class EmptySparseModel(FakeFlagModel):
            def encode_queries(
                self,
                queries: list[str],
                **kwargs: object,
            ) -> dict[str, list[list[float]] | list[dict[int, float]]]:
                self.encode_queries_calls.append({"queries": queries, "kwargs": kwargs})
                return {"dense_vecs": [[1.0] * 4], "lexical_weights": [{}]}

        with patch("FlagEmbedding.BGEM3FlagModel", EmptySparseModel):
            runtime = BgeM3FlagEmbeddingRuntime(settings=runtime_settings)
            with pytest.raises(
                EmbeddingRuntimeError,
                match="no non-zero sparse entries",
            ):
                runtime.embed_query_sparse("empty sparse")


class TestDeviceValidation:
    def test_cpu_requires_no_accelerator(self) -> None:
        validate_device_available("cpu")

    def test_cuda_unavailable_raises(self) -> None:
        with (
            patch("torch.cuda.is_available", return_value=False),
            pytest.raises(EmbeddingDeviceError, match="cuda"),
        ):
            validate_device_available("cuda")

    def test_mps_unavailable_raises(self) -> None:
        with (
            patch("torch.backends.mps.is_available", return_value=False),
            pytest.raises(EmbeddingDeviceError, match="mps"),
        ):
            validate_device_available("mps")


class TestL2Normalize:
    def test_normalizes_non_unit_vector(self) -> None:
        vector = (3.0, 4.0)
        normalized = l2_normalize(vector)
        norm = math.sqrt(sum(value * value for value in normalized))
        assert math.isclose(norm, 1.0, rel_tol=1e-6)
