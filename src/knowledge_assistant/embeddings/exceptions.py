"""Embedding runtime exception types."""


class EmbeddingRuntimeError(Exception):
    """Base error for dense embedding runtime failures."""


class EmbeddingDimensionMismatchError(EmbeddingRuntimeError):
    """Raised when model output dimension does not match configured size."""


class EmbeddingDeviceError(EmbeddingRuntimeError):
    """Raised when the configured inference device is unavailable."""
