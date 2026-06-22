"""Query embedding provider boundary for dense and sparse retrieval."""

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol

from knowledge_assistant.embeddings.runtime import DenseEmbeddingRuntime
from knowledge_assistant.retrieval.sparse_vectors import SparseQueryVector

QueryEmbeddingVector = tuple[float, ...]
_MAX_QUERY_TERMS = 32
_INDEX_MODULUS = 1_000_003


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


@dataclass(frozen=True, slots=True)
class BgeM3QueryEmbeddingProvider:
    """Dense query-path provider delegating to a shared embedding runtime."""

    runtime: DenseEmbeddingRuntime

    def embed_query(self, text: str) -> QueryEmbeddingVector:
        return self.runtime.embed_query(text)


@dataclass(frozen=True, slots=True)
class BgeM3SparseQueryEmbeddingProvider:
    """Sparse query-path provider delegating to a shared embedding runtime."""

    runtime: DenseEmbeddingRuntime

    def embed_query(self, text: str) -> SparseQueryVector:
        indices, values = self.runtime.embed_query_sparse(text)
        return SparseQueryVector(indices=indices, values=values)


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


class SparseQueryEmbeddingProvider(Protocol):
    """Generate sparse embeddings for search queries on the read path."""

    def embed_query(self, text: str) -> SparseQueryVector:
        """Return one sparse embedding for a search query."""
        ...


@dataclass(frozen=True, slots=True)
class StubSparseQueryEmbeddingProvider:
    """Hash-based sparse query embedding stub for tests without model runtime."""

    max_terms: int = _MAX_QUERY_TERMS
    index_modulus: int = _INDEX_MODULUS

    def embed_query(self, text: str) -> SparseQueryVector:
        return _hash_embed_sparse_query(
            text,
            max_terms=self.max_terms,
            index_modulus=self.index_modulus,
        )


def _hash_embed_sparse_query(
    text: str,
    *,
    max_terms: int,
    index_modulus: int,
) -> SparseQueryVector:
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

    return SparseQueryVector(indices=indices, values=values)
