"""Reranking orchestration for retrieved search candidates."""

import re
from collections.abc import Callable
from importlib import import_module
from typing import Protocol, cast

from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.retrieval.config import (
    BgeRerankerSettings,
    RerankRetrievalSettings,
)
from knowledge_assistant.retrieval.protocol import Retriever

_TOKEN_PATTERN = re.compile(r"\w+")


class BgeRerankerBackend(Protocol):
    """Minimal backend contract for BGE pair scoring."""

    def compute_scores(
        self,
        pairs: list[tuple[str, str]],
        *,
        batch_size: int,
        max_length: int,
    ) -> list[float]:
        """Return one relevance score per query/document pair."""
        ...


BgeRerankerModelLoader = Callable[[BgeRerankerSettings], BgeRerankerBackend]


class _FlagRerankerRuntime(Protocol):
    def compute_score(
        self,
        pairs: list[list[str]],
        *,
        batch_size: int,
        max_length: int,
    ) -> object: ...


class _FlagRerankerFactory(Protocol):
    def __call__(
        self,
        model_name_or_path: str,
        *,
        use_fp16: bool,
        devices: str | None = None,
    ) -> _FlagRerankerRuntime: ...


class _FlagEmbeddingRerankerBackend:
    """Adapter around FlagEmbedding's BGE reranker API."""

    def __init__(self, runtime: _FlagRerankerRuntime) -> None:
        self._runtime = runtime

    def compute_scores(
        self,
        pairs: list[tuple[str, str]],
        *,
        batch_size: int,
        max_length: int,
    ) -> list[float]:
        raw_pairs = [[query_text, chunk_text] for query_text, chunk_text in pairs]
        raw_scores = self._runtime.compute_score(
            raw_pairs,
            batch_size=batch_size,
            max_length=max_length,
        )
        return _coerce_scores(raw_scores)


def load_flag_embedding_reranker_backend(
    settings: BgeRerankerSettings,
) -> BgeRerankerBackend:
    """Load the FlagEmbedding BGE reranker backend lazily."""
    module = import_module("FlagEmbedding")
    factory = cast("_FlagRerankerFactory", module.FlagReranker)
    device = None if settings.device == "auto" else settings.device
    runtime = factory(
        settings.model_name,
        use_fp16=settings.use_fp16,
        devices=device,
    )
    return _FlagEmbeddingRerankerBackend(runtime)


def _coerce_scores(raw_scores: object) -> list[float]:
    if isinstance(raw_scores, int | float):
        return [float(raw_scores)]
    if not isinstance(raw_scores, list | tuple):
        msg = "BGE reranker backend returned an unsupported score shape"
        raise TypeError(msg)
    scores = cast("list[object] | tuple[object, ...]", raw_scores)
    return [_coerce_score(score) for score in scores]


def _coerce_score(score: object) -> float:
    if isinstance(score, int | float):
        return float(score)
    msg = "BGE reranker backend returned a non-numeric score"
    raise TypeError(msg)


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
                source=candidate.source,
            )
            for candidate in candidates
        ]
        return _sort_reranked_candidates(scored)


class BgeReranker:
    """BGE cross-encoder reranker behind the retrieval Reranker protocol."""

    def __init__(
        self,
        *,
        settings: BgeRerankerSettings,
        model_loader: BgeRerankerModelLoader | None = None,
    ) -> None:
        self._settings = settings
        self._model_loader = model_loader or load_flag_embedding_reranker_backend
        self._backend: BgeRerankerBackend | None = None

    @property
    def settings(self) -> BgeRerankerSettings:
        """Return immutable runtime settings without loading the model."""
        return self._settings

    @property
    def is_loaded(self) -> bool:
        """Return whether the lazy model backend has been loaded."""
        return self._backend is not None

    def rerank(
        self,
        query: SearchQuery,
        candidates: tuple[SearchResult, ...],
    ) -> tuple[SearchResult, ...]:
        """Score candidates with BGE and return all candidates reordered."""
        if not candidates:
            return ()

        backend = self._load_backend()
        pairs = [(query.text, candidate.chunk.text) for candidate in candidates]
        scores = backend.compute_scores(
            pairs,
            batch_size=self._settings.batch_size,
            max_length=self._settings.max_length,
        )
        if len(scores) != len(candidates):
            expected = len(candidates)
            actual = len(scores)
            msg = f"BGE reranker returned {actual} scores for {expected} candidates"
            raise ValueError(msg)

        scored = [
            SearchResult(
                chunk=candidate.chunk,
                score=score,
                source=candidate.source,
            )
            for candidate, score in zip(candidates, scores, strict=True)
        ]
        return _sort_reranked_candidates(scored)

    def _load_backend(self) -> BgeRerankerBackend:
        if self._backend is None:
            self._backend = self._model_loader(self._settings)
        return self._backend


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
