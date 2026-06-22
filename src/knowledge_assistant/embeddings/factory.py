"""Dense embedding runtime factory."""

from __future__ import annotations

from functools import cache

from knowledge_assistant.embeddings.config import EmbeddingRuntimeSettings
from knowledge_assistant.embeddings.runtime import (
    BgeM3FlagEmbeddingRuntime,
    DenseEmbeddingRuntime,
    validate_device_available,
)


def create_dense_embedding_runtime(
    settings: EmbeddingRuntimeSettings,
) -> DenseEmbeddingRuntime:
    """Construct a dense embedding runtime for the given settings.

    Device availability is validated before model construction. When ``device`` is
    ``cuda`` or ``mps`` but the accelerator is unavailable, raises
    ``EmbeddingDeviceError`` without falling back to CPU.
    """
    validate_device_available(settings.device)
    return BgeM3FlagEmbeddingRuntime(settings=settings)


@cache
def _cached_dense_embedding_runtime(
    model_name: str,
    device: str,
    batch_size: int,
    max_length: int,
    normalize_embeddings: bool,
    dense_vector_size: int,
) -> DenseEmbeddingRuntime:
    settings = EmbeddingRuntimeSettings(
        model_name=model_name,
        device=device,  # type: ignore[arg-type]
        batch_size=batch_size,
        max_length=max_length,
        normalize_embeddings=normalize_embeddings,
        dense_vector_size=dense_vector_size,
    )
    return create_dense_embedding_runtime(settings)


def create_shared_dense_embedding_runtime(
    settings: EmbeddingRuntimeSettings,
) -> DenseEmbeddingRuntime:
    """Return a process-local cached runtime keyed by settings fingerprint."""
    return _cached_dense_embedding_runtime(
        settings.model_name,
        settings.device,
        settings.batch_size,
        settings.max_length,
        settings.normalize_embeddings,
        settings.dense_vector_size,
    )


def clear_dense_embedding_runtime_cache() -> None:
    """Clear the process-local runtime cache (for tests)."""
    _cached_dense_embedding_runtime.cache_clear()
