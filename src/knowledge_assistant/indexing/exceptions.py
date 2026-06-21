"""Indexing-layer exception types."""


class IndexingError(Exception):
    """Base exception for indexing failures."""


class UnsupportedSourceKindError(IndexingError):
    """Raised when an indexing source kind is not supported."""


class UnsupportedFileTypeError(IndexingError):
    """Raised when a file extension is not supported for indexing."""


class SourceNotFoundError(IndexingError):
    """Raised when a source path does not exist."""


class DocumentLoadError(IndexingError):
    """Raised when a document cannot be loaded."""


class ChunkingError(IndexingError):
    """Raised when document chunking fails."""


class EmbeddingDimensionError(IndexingError):
    """Raised when an embedding vector has an unexpected dimension."""
