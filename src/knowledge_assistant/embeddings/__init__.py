"""Shared dense embedding runtime for BGE-M3 inference."""

from knowledge_assistant.embeddings.config import (
    DEFAULT_EMBEDDING_BATCH_SIZE,
    DEFAULT_EMBEDDING_DEVICE,
    DEFAULT_EMBEDDING_MAX_LENGTH,
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingRuntimeSettings,
)
from knowledge_assistant.embeddings.exceptions import (
    EmbeddingDeviceError,
    EmbeddingDimensionMismatchError,
    EmbeddingRuntimeError,
)
from knowledge_assistant.embeddings.factory import (
    clear_dense_embedding_runtime_cache,
    create_dense_embedding_runtime,
    create_shared_dense_embedding_runtime,
)
from knowledge_assistant.embeddings.runtime import (
    BgeM3FlagEmbeddingRuntime,
    DenseEmbeddingRuntime,
)
from knowledge_assistant.embeddings.sparse_conversion import (
    SparseVectorPayload,
    lexical_weights_to_sparse_payload,
)

__all__ = [
    "DEFAULT_EMBEDDING_BATCH_SIZE",
    "DEFAULT_EMBEDDING_DEVICE",
    "DEFAULT_EMBEDDING_MAX_LENGTH",
    "DEFAULT_EMBEDDING_MODEL",
    "BgeM3FlagEmbeddingRuntime",
    "DenseEmbeddingRuntime",
    "EmbeddingDeviceError",
    "EmbeddingDimensionMismatchError",
    "EmbeddingRuntimeError",
    "EmbeddingRuntimeSettings",
    "SparseVectorPayload",
    "clear_dense_embedding_runtime_cache",
    "create_dense_embedding_runtime",
    "create_shared_dense_embedding_runtime",
    "lexical_weights_to_sparse_payload",
]
