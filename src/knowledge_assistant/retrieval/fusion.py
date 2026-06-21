"""Hybrid retrieval fusion orchestration."""

from knowledge_assistant.core.identifiers import ChunkId
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.retrieval.config import FusionRetrievalSettings
from knowledge_assistant.retrieval.protocol import Retriever

_RankEntry = tuple[int, int, SearchResult]


def _chunk_rank_map(
    results: tuple[SearchResult, ...],
    *,
    list_priority: int,
) -> dict[ChunkId, _RankEntry]:
    """Map each chunk to its first (best) rank within one leaf ranked list."""
    mapping: dict[ChunkId, _RankEntry] = {}
    for rank, result in enumerate(results, start=1):
        chunk_id = result.chunk.chunk_id
        if chunk_id not in mapping:
            mapping[chunk_id] = (rank, list_priority, result)
    return mapping


def _select_best_chunk_entry(
    dense_map: dict[ChunkId, _RankEntry],
    sparse_map: dict[ChunkId, _RankEntry],
    chunk_id: ChunkId,
) -> SearchResult:
    """Return the chunk payload from the best-ranked occurrence across leaf lists."""
    candidates = [
        entry
        for entry in (dense_map.get(chunk_id), sparse_map.get(chunk_id))
        if entry is not None
    ]
    _, _, best_result = min(candidates, key=lambda entry: (entry[0], entry[1]))
    return best_result


def reciprocal_rank_fusion(
    *,
    dense_results: tuple[SearchResult, ...],
    sparse_results: tuple[SearchResult, ...],
    rrf_k: int,
) -> tuple[SearchResult, ...]:
    """Fuse two ranked result lists with RRF.

    Returns all candidates sorted by fused score.
    """
    if rrf_k < 1:
        raise ValueError("rrf_k must be >= 1")

    dense_map = _chunk_rank_map(dense_results, list_priority=0)
    sparse_map = _chunk_rank_map(sparse_results, list_priority=1)

    fused_scores: list[tuple[float, ChunkId, SearchResult]] = []
    for chunk_id in dense_map.keys() | sparse_map.keys():
        score = 0.0
        if chunk_id in dense_map:
            rank, _, _ = dense_map[chunk_id]
            score += 1.0 / (rrf_k + rank)
        if chunk_id in sparse_map:
            rank, _, _ = sparse_map[chunk_id]
            score += 1.0 / (rrf_k + rank)

        best_result = _select_best_chunk_entry(dense_map, sparse_map, chunk_id)
        fused_scores.append(
            (
                score,
                chunk_id,
                SearchResult(chunk=best_result.chunk, score=score),
            ),
        )

    fused_scores.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[2] for item in fused_scores)


class FusionRetriever:
    """Orchestrates dense and sparse leaf retrievers with reciprocal rank fusion."""

    def __init__(
        self,
        *,
        dense_retriever: Retriever,
        sparse_retriever: Retriever,
        settings: FusionRetrievalSettings,
    ) -> None:
        self._dense_retriever = dense_retriever
        self._sparse_retriever = sparse_retriever
        self._settings = settings

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        """Fuse dense and sparse leaf retrieval results for the caller query."""
        leaf_top_k = self._settings.resolve_leaf_top_k(query.top_k)
        leaf_query = SearchQuery(text=query.text, top_k=leaf_top_k)

        dense_result = self._dense_retriever.retrieve(leaf_query)
        sparse_result = self._sparse_retriever.retrieve(leaf_query)

        fused = reciprocal_rank_fusion(
            dense_results=dense_result.results,
            sparse_results=sparse_result.results,
            rrf_k=self._settings.rrf_k,
        )
        return RetrievalResult(query=query, results=fused[: query.top_k])
