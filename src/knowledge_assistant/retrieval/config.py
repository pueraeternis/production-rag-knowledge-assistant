"""Retrieval configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DenseRetrievalSettings:
    """Configuration for dense retrieval and query embedding dimensions."""

    dense_vector_size: int = 1024

    def __post_init__(self) -> None:
        if self.dense_vector_size <= 0:
            msg = "dense_vector_size must be > 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class FusionRetrievalSettings:
    """Configuration for hybrid rank-based fusion."""

    rrf_k: int = 60
    leaf_top_k_multiplier: int = 2

    def __post_init__(self) -> None:
        if self.rrf_k < 1:
            msg = "rrf_k must be >= 1"
            raise ValueError(msg)
        if self.leaf_top_k_multiplier < 1:
            msg = "leaf_top_k_multiplier must be >= 1"
            raise ValueError(msg)

    def resolve_leaf_top_k(self, query_top_k: int) -> int:
        """Candidate pool size forwarded to each leaf retriever."""
        return query_top_k * self.leaf_top_k_multiplier


@dataclass(frozen=True, slots=True)
class RerankRetrievalSettings:
    """Configuration for reranked retrieval candidate pool expansion."""

    candidate_top_k_multiplier: int = 2

    def __post_init__(self) -> None:
        if self.candidate_top_k_multiplier < 1:
            msg = "candidate_top_k_multiplier must be >= 1"
            raise ValueError(msg)

    def resolve_candidate_top_k(self, query_top_k: int) -> int:
        """Candidate pool size forwarded to the base retriever."""
        return query_top_k * self.candidate_top_k_multiplier
