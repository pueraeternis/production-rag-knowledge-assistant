"""LlamaIndex ingestion and chunking for the knowledge assistant."""

from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.embeddings import (
    EmbeddingProvider,
    StubEmbeddingProvider,
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
    "ChunkingError",
    "DocumentLoadError",
    "EmbeddingDimensionError",
    "EmbeddingProvider",
    "IndexingError",
    "IndexingPipeline",
    "IndexingResult",
    "IndexingSettings",
    "SourceNotFoundError",
    "StubEmbeddingProvider",
    "UnsupportedFileTypeError",
    "UnsupportedSourceKindError",
]
