"""Retrieval-layer exception types."""


class RetrievalError(Exception):
    """Base exception for retrieval failures."""


class RetrievalConfigurationError(RetrievalError):
    """Raised when retrieval configuration is invalid."""


class EmbeddingDimensionError(RetrievalError):
    """Raised when an embedding vector has an unexpected dimension."""


class SparseVectorValidationError(RetrievalError):
    """Raised when a sparse query vector fails retrieval-local validation."""
