"""Embedding provider boundary and sparse vector generation for indexing."""

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol

from knowledge_assistant.embeddings.runtime import DenseEmbeddingRuntime
from knowledge_assistant.storage.models import SparseVector

EmbeddingVector = tuple[float, ...]
_MAX_SPARSE_TERMS = 32
_INDEX_MODULUS = 1_000_003


class EmbeddingProvider(Protocol):
    """Generate dense embeddings for document chunks on the write path."""

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[EmbeddingVector, ...]:
        """Return one dense embedding per input text, in the same order."""
        ...


class SparseEmbeddingProvider(Protocol):
    """Generate sparse embeddings for document chunks on the write path."""

    def embed_sparse_texts(self, texts: tuple[str, ...]) -> tuple[SparseVector, ...]:
        """Return one sparse embedding per input text, in the same order."""
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


@dataclass(frozen=True, slots=True)
class BgeM3EmbeddingProvider:
    """Dense write-path provider delegating to a shared embedding runtime."""

    runtime: DenseEmbeddingRuntime

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[EmbeddingVector, ...]:
        return self.runtime.embed_passages(texts)


@dataclass(frozen=True, slots=True)
class StubSparseEmbeddingProvider:
    """Hash-based sparse embedding stub for tests without model runtime."""

    max_terms: int = _MAX_SPARSE_TERMS
    index_modulus: int = _INDEX_MODULUS

    def embed_sparse_texts(self, texts: tuple[str, ...]) -> tuple[SparseVector, ...]:
        return tuple(
            _hash_embed_sparse_text(
                text,
                max_terms=self.max_terms,
                index_modulus=self.index_modulus,
            )
            for text in texts
        )


@dataclass(frozen=True, slots=True)
class BgeM3SparseEmbeddingProvider:
    """Sparse write-path provider delegating to a shared embedding runtime."""

    runtime: DenseEmbeddingRuntime

    def embed_sparse_texts(self, texts: tuple[str, ...]) -> tuple[SparseVector, ...]:
        payloads = self.runtime.embed_passages_sparse(texts)
        return tuple(
            SparseVector(indices=indices, values=values) for indices, values in payloads
        )


def sparse_placeholder_vector() -> SparseVector:
    """Return a constant sparse placeholder for legacy unit tests."""
    return SparseVector(indices=(0,), values=(1.0,))


def _hash_embed_sparse_text(
    text: str,
    *,
    max_terms: int,
    index_modulus: int,
) -> SparseVector:
    normalized = text.strip()
    terms = re.split(r"\s+", normalized)
    terms = [term for term in terms if term][:max_terms]

    index_weights: dict[int, float] = {}
    for term in terms:
        digest = hashlib.sha256(term.encode("utf-8")).digest()
        index = int.from_bytes(digest[:8], "big") % index_modulus
        weight = 1.0 + (digest[8] / 255.0)
        index_weights[index] = index_weights.get(index, 0.0) + weight

    indices = tuple(sorted(index_weights))
    raw_values = tuple(index_weights[index] for index in indices)
    norm = math.sqrt(sum(value * value for value in raw_values))
    values = tuple(value / norm for value in raw_values) if norm > 0 else raw_values

    return SparseVector(indices=indices, values=values)
