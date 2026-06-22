"""LlamaIndex ingestion and chunking for the knowledge assistant."""

from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.embeddings import (
    BgeM3EmbeddingProvider,
    BgeM3SparseEmbeddingProvider,
    EmbeddingProvider,
    SparseEmbeddingProvider,
    StubEmbeddingProvider,
    StubSparseEmbeddingProvider,
)
from knowledge_assistant.indexing.exceptions import (
    ChunkingError,
    DocumentLoadError,
    EmbeddingDimensionError,
    IndexingError,
    SourceNotFoundError,
    UnsupportedFileTypeError,
    UnsupportedSourceKindError,
)
from knowledge_assistant.indexing.pipeline import IndexingPipeline, IndexingResult

__all__ = [
    "BgeM3EmbeddingProvider",
    "BgeM3SparseEmbeddingProvider",
    "ChunkingError",
    "DocumentLoadError",
    "EmbeddingDimensionError",
    "EmbeddingProvider",
    "IndexingError",
    "IndexingPipeline",
    "IndexingResult",
    "IndexingSettings",
    "SourceNotFoundError",
    "SparseEmbeddingProvider",
    "StubEmbeddingProvider",
    "StubSparseEmbeddingProvider",
    "UnsupportedFileTypeError",
    "UnsupportedSourceKindError",
]
