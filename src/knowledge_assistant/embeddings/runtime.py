"""Dense embedding runtime protocol and BGE-M3 FlagEmbedding implementation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Protocol, cast, runtime_checkable

import numpy as np
import torch

from knowledge_assistant.embeddings.config import EmbeddingRuntimeSettings
from knowledge_assistant.embeddings.exceptions import (
    EmbeddingDeviceError,
    EmbeddingDimensionMismatchError,
)


@runtime_checkable
class DenseEmbeddingRuntime(Protocol):
    """
    Stable contract for dense embedding inference.

    ``embed_passages`` batches texts with ``EmbeddingRuntimeSettings.batch_size``.
    ``embed_query`` always processes one query (no batching).

    Thread safety is not guaranteed. Callers must not invoke ``embed_passages`` or
    ``embed_query`` concurrently on the same runtime instance from multiple threads.
    Runtime instances are intended for single-process demo wiring, indexing batches,
    and sequential retrieval queries.
    """

    def embed_passages(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Return one dense embedding per passage text, preserving input order."""
        ...

    def embed_query(self, text: str) -> tuple[float, ...]:
        """Return one dense embedding for a single search query."""
        ...


def validate_device_available(device: str) -> None:
    """Raise ``EmbeddingDeviceError`` when an accelerator device is unavailable."""
    if device == "cpu":
        return

    if device == "cuda" and not torch.cuda.is_available():
        msg = (
            "configured embedding device 'cuda' is unavailable; "
            "automatic CPU fallback is disabled"
        )
        raise EmbeddingDeviceError(msg)
    if device == "mps" and not torch.backends.mps.is_available():
        msg = (
            "configured embedding device 'mps' is unavailable; "
            "automatic CPU fallback is disabled"
        )
        raise EmbeddingDeviceError(msg)


def l2_normalize(vector: tuple[float, ...]) -> tuple[float, ...]:
    """Return an L2-normalized copy of ``vector``."""
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0:
        return vector
    return tuple(value / norm for value in vector)


def validate_vector_dimension(
    vector: tuple[float, ...],
    *,
    expected_size: int,
) -> tuple[float, ...]:
    """Validate vector length and optionally normalize."""
    actual_size = len(vector)
    if actual_size != expected_size:
        msg = (
            f"embedding dimension mismatch: expected {expected_size}, got {actual_size}"
        )
        raise EmbeddingDimensionMismatchError(msg)
    return vector


class _BgeM3ModelFactory(Protocol):
    def __call__(
        self,
        model_name_or_path: str,
        *,
        use_fp16: bool,
        devices: str,
    ) -> object: ...


def _vector_rows_from_dense_output(dense_vecs: object) -> list[tuple[float, ...]]:
    """
    Normalize FlagEmbedding dense outputs into validated vector rows.

    FlagEmbedding returns ``list[list[float]]`` on CPU and ``numpy.ndarray`` with
    shape ``(batch_size, dimension)`` on CUDA. Both shapes must be accepted.
    """
    if isinstance(dense_vecs, list):
        return _vector_rows_from_sequence(cast("list[object]", dense_vecs))

    ndarray_rows = _vector_rows_from_ndarray(dense_vecs)
    if ndarray_rows is not None:
        return ndarray_rows

    tensor_rows = _vector_rows_from_tensor(dense_vecs)
    if tensor_rows is not None:
        return tensor_rows

    msg = "BGE-M3 runtime returned unsupported dense_vecs shape"
    raise TypeError(msg)


def _vector_rows_from_sequence(rows: list[object]) -> list[tuple[float, ...]]:
    vectors: list[tuple[float, ...]] = []
    for row in rows:
        if not isinstance(row, list | tuple):
            msg = "BGE-M3 runtime returned unsupported dense vector row"
            raise TypeError(msg)
        values = cast("list[object] | tuple[object, ...]", row)
        vectors.append(
            tuple(float(cast("float | int", value)) for value in values),
        )
    return vectors


def _vector_rows_from_ndarray(dense_vecs: object) -> list[tuple[float, ...]] | None:
    if not isinstance(dense_vecs, np.ndarray):
        return None

    if dense_vecs.ndim == 1:
        row: object = dense_vecs.tolist()
        return [_vector_rows_from_sequence([row])[0]]
    if dense_vecs.ndim == 2:
        rows: list[object] = dense_vecs.tolist()
        return _vector_rows_from_sequence(rows)

    msg = "BGE-M3 runtime returned unsupported dense_vecs shape"
    raise TypeError(msg)


def _vector_rows_from_tensor(dense_vecs: object) -> list[tuple[float, ...]] | None:
    detach = getattr(dense_vecs, "detach", None)
    if not callable(detach):
        return None

    tensor: Any = detach()
    cpu = getattr(tensor, "cpu", None)
    if not callable(cpu):
        return None

    tensor_on_cpu: Any = cpu()
    tolist = getattr(tensor_on_cpu, "tolist", None)
    if not callable(tolist):
        return None

    rows: Any = tolist()
    if isinstance(rows, list) and rows and isinstance(rows[0], int | float):
        return _vector_rows_from_sequence([rows])
    if isinstance(rows, list):
        return _vector_rows_from_sequence(cast("list[object]", rows))

    msg = "BGE-M3 runtime returned unsupported dense_vecs shape"
    raise TypeError(msg)


@dataclass(slots=True)
class BgeM3FlagEmbeddingRuntime:
    """BGE-M3 dense embedding runtime using FlagEmbedding internally."""

    settings: EmbeddingRuntimeSettings
    _model: object = field(init=False, repr=False)

    def __post_init__(self) -> None:
        validate_device_available(self.settings.device)
        self._model = self._load_model()

    def _load_model(self) -> object:
        module = import_module("FlagEmbedding")
        model_factory = cast("_BgeM3ModelFactory", module.BGEM3FlagModel)
        use_fp16 = self.settings.device != "cpu"
        return model_factory(
            self.settings.model_name,
            use_fp16=use_fp16,
            devices=self.settings.device,
        )

    def embed_passages(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        raw_vectors = self._encode_passages(texts)
        return tuple(self._finalize_vector(vector) for vector in raw_vectors)

    def embed_query(self, text: str) -> tuple[float, ...]:
        raw_vector = self._encode_query(text)
        return self._finalize_vector(raw_vector)

    def _encode_passages(self, texts: tuple[str, ...]) -> list[tuple[float, ...]]:
        output = cast(
            "dict[str, object]",
            self._model.encode(  # type: ignore[attr-defined]
                list(texts),
                batch_size=self.settings.batch_size,
                max_length=self.settings.max_length,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            ),
        )
        return _vector_rows_from_dense_output(output["dense_vecs"])

    def _encode_query(self, text: str) -> tuple[float, ...]:
        output = cast(
            "dict[str, object]",
            self._model.encode_queries(  # type: ignore[attr-defined]
                [text],
                max_length=self.settings.max_length,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            ),
        )
        rows = _vector_rows_from_dense_output(output["dense_vecs"])
        return rows[0]

    def _finalize_vector(self, vector: tuple[float, ...]) -> tuple[float, ...]:
        validated = validate_vector_dimension(
            vector,
            expected_size=self.settings.dense_vector_size,
        )
        if self.settings.normalize_embeddings:
            return l2_normalize(validated)
        return validated
