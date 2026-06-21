"""Embedding provider boundary and sparse vector placeholder for indexing."""

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol

from knowledge_assistant.storage.models import SparseVector

EmbeddingVector = tuple[float, ...]


class EmbeddingProvider(Protocol):
    """Generate dense embeddings for document chunks on the write path."""

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[EmbeddingVector, ...]:
        """Return one dense embedding per input text, in the same order."""
        ...


@dataclass(frozen=True, slots=True)
class StubEmbeddingProvider:
    """Hash-based embedding stub for tests and development without model runtime."""

    dimension: int = 1024

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[EmbeddingVector, ...]:
        return tuple(self._embed_text(text) for text in texts)

    def _embed_text(self, text: str) -> EmbeddingVector:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        counter = 0
        while len(values) < self.dimension:
            expanded = hashlib.sha256(
                digest + counter.to_bytes(4, "big"),
            ).digest()
            values.extend((byte / 127.5) - 1.0 for byte in expanded)
            counter += 1
        vector = values[: self.dimension]
        norm = math.sqrt(sum(value * value for value in vector))
        if norm > 0:
            vector = [value / norm for value in vector]
        return tuple(vector)


def sparse_placeholder_vector() -> SparseVector:
    """Return a constant sparse placeholder until real sparse vectors are available."""
    return SparseVector(indices=(0,), values=(1.0,))
