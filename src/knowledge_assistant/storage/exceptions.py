"""Storage-layer exception types."""


class StorageError(Exception):
    """Base exception for storage-layer failures."""


class CollectionAlreadyExistsError(StorageError):
    """Raised when creating a collection that already exists."""


class CollectionNotFoundError(StorageError):
    """Raised when an operation targets a missing collection."""


class VectorDimensionError(StorageError):
    """Raised when a vector length does not match the configured dimension."""


class PayloadMappingError(StorageError):
    """Raised when a Qdrant payload cannot be mapped to a domain model."""


class InvalidChunkIdError(StorageError):
    """Raised when a ChunkId is not a valid UUID string for Qdrant point IDs."""
