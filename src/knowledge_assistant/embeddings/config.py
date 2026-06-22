"""Dense embedding runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Self

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"
DEFAULT_EMBEDDING_DEVICE = "cpu"
DEFAULT_EMBEDDING_BATCH_SIZE = 32
DEFAULT_EMBEDDING_MAX_LENGTH = 8192

EmbeddingDevice = Literal["cpu", "cuda", "mps"]


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    msg = f"invalid boolean value: {value!r}"
    raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class EmbeddingRuntimeSettings:
    """Configuration for BGE-M3 dense embedding inference."""

    model_name: str = DEFAULT_EMBEDDING_MODEL
    device: EmbeddingDevice = DEFAULT_EMBEDDING_DEVICE
    batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE
    max_length: int = DEFAULT_EMBEDDING_MAX_LENGTH
    normalize_embeddings: bool = True
    dense_vector_size: int = 1024

    def __post_init__(self) -> None:
        if not self.model_name.strip():
            msg = "EmbeddingRuntimeSettings.model_name must be non-empty"
            raise ValueError(msg)
        if self.device not in ("cpu", "cuda", "mps"):
            msg = (
                "EmbeddingRuntimeSettings.device must be one of 'cpu', 'cuda', or 'mps'"
            )
            raise ValueError(msg)
        if self.batch_size <= 0:
            msg = "EmbeddingRuntimeSettings.batch_size must be > 0"
            raise ValueError(msg)
        if self.max_length <= 0:
            msg = "EmbeddingRuntimeSettings.max_length must be > 0"
            raise ValueError(msg)
        if self.dense_vector_size <= 0:
            msg = "EmbeddingRuntimeSettings.dense_vector_size must be > 0"
            raise ValueError(msg)

    @classmethod
    def from_env(cls, *, dense_vector_size: int, **overrides: object) -> Self:
        """Build settings from ``RAG_EMBEDDING_*`` environment variables."""
        model_name = os.environ.get("RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        device_raw = os.environ.get("RAG_EMBEDDING_DEVICE", DEFAULT_EMBEDDING_DEVICE)
        batch_size = int(
            os.environ.get(
                "RAG_EMBEDDING_BATCH_SIZE",
                str(DEFAULT_EMBEDDING_BATCH_SIZE),
            ),
        )
        max_length = int(
            os.environ.get(
                "RAG_EMBEDDING_MAX_LENGTH",
                str(DEFAULT_EMBEDDING_MAX_LENGTH),
            ),
        )
        normalize_raw = os.environ.get("RAG_EMBEDDING_NORMALIZE", "true")
        normalize_embeddings = _parse_bool(normalize_raw)

        if device_raw not in ("cpu", "cuda", "mps"):
            msg = (
                "RAG_EMBEDDING_DEVICE must be one of 'cpu', 'cuda', or 'mps'; "
                f"got {device_raw!r}"
            )
            raise ValueError(msg)

        settings_kwargs: dict[str, object] = {
            "model_name": model_name.strip(),
            "device": device_raw,
            "batch_size": batch_size,
            "max_length": max_length,
            "normalize_embeddings": normalize_embeddings,
            "dense_vector_size": dense_vector_size,
        }
        settings_kwargs.update(overrides)
        return cls(**settings_kwargs)  # type: ignore[arg-type]
