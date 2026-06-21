"""Reranking orchestration for retrieved search candidates."""

import re
from typing import Protocol

from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.retrieval.config import RerankRetrievalSettings
from knowledge_assistant.retrieval.protocol import Retriever

_TOKEN_PATTERN = re.compile(r"\w+")


class Reranker(Protocol):
    """Score and reorder retrieval candidates for one search query."""

    def rerank(
        self,
        query: SearchQuery,
        candidates: tuple[SearchResult, ...],
    ) -> tuple[SearchResult, ...]:
        """Score and reorder retrieval candidates for one search query."""
        ...


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(_TOKEN_PATTERN.findall(text.lower()))


def stub_rerank_score(query_text: str, chunk_text: str) -> float:
    """Deterministic Jaccard token overlap score in [0.0, 1.0]."""
    query_tokens = _tokenize(query_text)
    chunk_tokens = _tokenize(chunk_text)
    if not query_tokens or not chunk_tokens:
        return 0.0
    intersection = len(query_tokens & chunk_tokens)
    union = len(query_tokens | chunk_tokens)
    return intersection / union


def _sort_reranked_candidates(
    scored: list[SearchResult],
) -> tuple[SearchResult, ...]:
    scored.sort(key=lambda result: (-result.score, result.chunk.chunk_id))
    return tuple(scored)


class StubReranker:
    """Deterministic hash/lexical reranker stub without model runtime."""

    def rerank(
        self,
        query: SearchQuery,
        candidates: tuple[SearchResult, ...],
    ) -> tuple[SearchResult, ...]:
        """Score candidates by token overlap and return a reranked tuple."""
        if not candidates:
            return ()

        scored = [
            SearchResult(
                chunk=candidate.chunk,
                score=stub_rerank_score(query.text, candidate.chunk.text),
            )
            for candidate in candidates
        ]
        return _sort_reranked_candidates(scored)


class RerankRetriever:
    """Orchestrates base retrieval and reranking for caller search queries."""

    def __init__(
        self,
        *,
        base_retriever: Retriever,
        reranker: Reranker,
        settings: RerankRetrievalSettings,
    ) -> None:
        self._base_retriever = base_retriever
        self._reranker = reranker
        self._settings = settings

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        """Retrieve, rerank, and truncate candidates for the caller query."""
        candidate_top_k = self._settings.resolve_candidate_top_k(query.top_k)
        candidate_query = SearchQuery(text=query.text, top_k=candidate_top_k)

        base_result = self._base_retriever.retrieve(candidate_query)
        candidates = base_result.results

        if not candidates:
            return RetrievalResult(query=query, results=())

        reranked = self._reranker.rerank(query=query, candidates=candidates)

        if len(reranked) != len(candidates):
            expected = len(candidates)
            actual = len(reranked)
            msg = f"reranker must return {expected} candidates, got {actual}"
            raise ValueError(msg)

        return RetrievalResult(query=query, results=reranked[: query.top_k])
