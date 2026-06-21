"""Query embedding provider boundary for dense retrieval."""

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol

QueryEmbeddingVector = tuple[float, ...]


class QueryEmbeddingProvider(Protocol):
    """Generate dense embeddings for search queries on the read path."""

    def embed_query(self, text: str) -> QueryEmbeddingVector:
        """Return one dense embedding for a search query."""
        ...


@dataclass(frozen=True, slots=True)
class StubQueryEmbeddingProvider:
    """Hash-based query embedding stub for tests without model runtime."""

    dimension: int = 1024

    def embed_query(self, text: str) -> QueryEmbeddingVector:
        return _hash_embed_text(text, dimension=self.dimension)


def _hash_embed_text(text: str, *, dimension: int) -> QueryEmbeddingVector:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    counter = 0
    while len(values) < dimension:
        expanded = hashlib.sha256(
            digest + counter.to_bytes(4, "big"),
        ).digest()
        values.extend((byte / 127.5) - 1.0 for byte in expanded)
        counter += 1
    vector = values[:dimension]
    norm = math.sqrt(sum(value * value for value in vector))
    if norm > 0:
        vector = [value / norm for value in vector]
    return tuple(vector)
