"""Storage configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Self

from knowledge_assistant.storage.collection import (
    DEFAULT_COLLECTION_NAME,
    DEFAULT_DENSE_VECTOR_SIZE,
)


@dataclass(frozen=True, slots=True)
class StorageSettings:
    """Configuration for Qdrant-backed vector storage."""

    qdrant_url: str = "http://localhost:6333"
    collection_name: str = DEFAULT_COLLECTION_NAME
    dense_vector_size: int = DEFAULT_DENSE_VECTOR_SIZE

    @classmethod
    def from_env(cls, **overrides: object) -> Self:
        """Build settings with ``QDRANT_URL`` applied when present."""
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        return cls(qdrant_url=qdrant_url, **overrides)  # type: ignore[arg-type]
