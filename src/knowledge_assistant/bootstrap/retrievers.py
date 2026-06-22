"""Strategy retriever assembly for evaluation and demo workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from knowledge_assistant.bootstrap.config import BootstrapSettings

if TYPE_CHECKING:
    from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.retrieval import (
    BgeReranker,
    DenseRetriever,
    FusionRetrievalSettings,
    FusionRetriever,
    QueryEmbeddingProvider,
    RerankRetrievalSettings,
    RerankRetriever,
    Retriever,
    SparseRetriever,
    StubReranker,
    StubSparseQueryEmbeddingProvider,
)
from knowledge_assistant.storage import VectorStore

RetrievalStrategy = Literal["dense", "sparse", "fusion", "rerank"]

CANONICAL_STRATEGIES: tuple[RetrievalStrategy, ...] = (
    "dense",
    "sparse",
    "fusion",
    "rerank",
)

_STRATEGY_STACK_DESCRIPTIONS: dict[RetrievalStrategy, str] = {
    "dense": "DenseRetriever",
    "sparse": "SparseRetriever",
    "fusion": "FusionRetriever(DenseRetriever, SparseRetriever)",
    "rerank": "RerankRetriever(FusionRetriever(...), Reranker)",
}


@dataclass(frozen=True, slots=True)
class RetrievalStack:
    """Shared retrieval orchestrators built from one bootstrap environment."""

    dense_retriever: DenseRetriever
    sparse_retriever: SparseRetriever
    fusion_retriever: FusionRetriever
    rerank_retriever: RerankRetriever
    reranker: StubReranker | BgeReranker


def strategy_stack_description(strategy: RetrievalStrategy) -> str:
    """Return a human-readable stack description for the given strategy."""
    return _STRATEGY_STACK_DESCRIPTIONS[strategy]


def _build_reranker(settings: BootstrapSettings) -> StubReranker | BgeReranker:
    if settings.reranker_mode == "stub":
        return StubReranker()
    return BgeReranker(settings=settings.bge_reranker_settings)


def build_retrieval_stack(
    *,
    settings: BootstrapSettings,
    vector_store: VectorStore,
    query_embedding_provider: QueryEmbeddingProvider,
) -> RetrievalStack:
    """Build the shared dense/sparse/fusion/rerank stack for one vector store."""
    dense_retriever = DenseRetriever(
        vector_store=vector_store,
        embedding_provider=query_embedding_provider,
        settings=settings.dense_retrieval_settings,
    )
    sparse_retriever = SparseRetriever(
        vector_store=vector_store,
        embedding_provider=StubSparseQueryEmbeddingProvider(),
    )
    fusion_retriever = FusionRetriever(
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever,
        settings=FusionRetrievalSettings(),
    )
    reranker = _build_reranker(settings)
    rerank_retriever = RerankRetriever(
        base_retriever=fusion_retriever,
        reranker=reranker,
        settings=RerankRetrievalSettings(),
    )
    return RetrievalStack(
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever,
        fusion_retriever=fusion_retriever,
        rerank_retriever=rerank_retriever,
        reranker=reranker,
    )


def build_retriever_for_strategy(
    environment: DemoEnvironment,
    strategy: RetrievalStrategy,
) -> Retriever:
    """Return the orchestrator for a canonical retrieval strategy."""
    stack = environment.retrieval_stack
    return {
        "dense": stack.dense_retriever,
        "sparse": stack.sparse_retriever,
        "fusion": stack.fusion_retriever,
        "rerank": stack.rerank_retriever,
    }[strategy]


__all__ = (
    "CANONICAL_STRATEGIES",
    "RetrievalStack",
    "RetrievalStrategy",
    "build_retrieval_stack",
    "build_retriever_for_strategy",
    "strategy_stack_description",
)
