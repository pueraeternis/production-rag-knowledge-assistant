"""Unit tests for reciprocal rank fusion and FusionRetriever orchestration."""

from unittest.mock import MagicMock

import pytest

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.retrieval.config import FusionRetrievalSettings
from knowledge_assistant.retrieval.fusion import FusionRetriever, reciprocal_rank_fusion

RRF_K = 60


def _make_source() -> SourceReference:
    return SourceReference(
        document_title="Guide",
        document_path="docs/guide.md",
        section_title="Section",
        line_range=LineRange(start_line=1, end_line=5),
    )


def _make_chunk(chunk_id: str, text: str = "chunk text") -> Chunk:
    return Chunk(
        chunk_id=ChunkId(chunk_id),
        metadata=ChunkMetadata(
            document_id=DocumentId("doc-1"),
            section_title="Section",
            line_range=LineRange(start_line=1, end_line=5),
            chunk_index=0,
        ),
        text=text,
    )


def _make_result(
    chunk_id: str,
    score: float = 0.5,
    *,
    text: str = "chunk text",
) -> SearchResult:
    return SearchResult(
        chunk=_make_chunk(chunk_id, text=text),
        score=score,
        source=_make_source(),
    )


def _rrf_term(rank: int, rrf_k: int = RRF_K) -> float:
    return 1.0 / (rrf_k + rank)


class TestReciprocalRankFusion:
    def test_empty_both_lists_returns_empty_tuple(self) -> None:
        assert (
            reciprocal_rank_fusion(dense_results=(), sparse_results=(), rrf_k=RRF_K)
            == ()
        )

    @pytest.mark.parametrize("rrf_k", [0, -1])
    def test_invalid_rrf_k_raises_value_error(self, rrf_k: int) -> None:
        with pytest.raises(ValueError, match="rrf_k must be >= 1"):
            reciprocal_rank_fusion(dense_results=(), sparse_results=(), rrf_k=rrf_k)

    def test_empty_dense_uses_sparse_ranks_only(self) -> None:
        sparse = (_make_result("chunk-b"),)
        fused = reciprocal_rank_fusion(
            dense_results=(),
            sparse_results=sparse,
            rrf_k=RRF_K,
        )

        assert len(fused) == 1
        assert fused[0].chunk.chunk_id == ChunkId("chunk-b")
        assert fused[0].score == pytest.approx(_rrf_term(1))

    def test_empty_sparse_uses_dense_ranks_only(self) -> None:
        dense = (_make_result("chunk-a"),)
        fused = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=(),
            rrf_k=RRF_K,
        )

        assert len(fused) == 1
        assert fused[0].chunk.chunk_id == ChunkId("chunk-a")
        assert fused[0].score == pytest.approx(_rrf_term(1))

    def test_single_list_chunk_receives_one_rrf_term(self) -> None:
        dense = (_make_result("chunk-a"), _make_result("chunk-b"))
        fused = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=(),
            rrf_k=RRF_K,
        )

        assert fused[0].chunk.chunk_id == ChunkId("chunk-a")
        assert fused[0].score == pytest.approx(_rrf_term(1))
        assert fused[1].chunk.chunk_id == ChunkId("chunk-b")
        assert fused[1].score == pytest.approx(_rrf_term(2))

    def test_chunk_in_both_lists_receives_summed_rrf_terms(self) -> None:
        dense = (_make_result("chunk-shared"),)
        sparse = (_make_result("chunk-shared", text="sparse text"),)
        fused = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=sparse,
            rrf_k=RRF_K,
        )

        assert len(fused) == 1
        assert fused[0].score == pytest.approx(_rrf_term(1) + _rrf_term(1))

    def test_chunk_in_both_lists_scores_higher_than_single_list_presence(self) -> None:
        dense = (_make_result("chunk-shared"), _make_result("chunk-dense-only"))
        sparse = (_make_result("chunk-shared"), _make_result("chunk-sparse-only"))
        fused = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=sparse,
            rrf_k=RRF_K,
        )

        assert fused[0].chunk.chunk_id == ChunkId("chunk-shared")
        assert fused[0].score > fused[1].score
        assert fused[0].score > fused[2].score

    def test_duplicate_chunk_id_within_one_list_keeps_first_rank(self) -> None:
        dense = (
            _make_result("chunk-dup", score=0.9),
            _make_result("chunk-dup", score=0.1),
        )
        fused = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=(),
            rrf_k=RRF_K,
        )

        assert len(fused) == 1
        assert fused[0].score == pytest.approx(_rrf_term(1))

    def test_tie_on_rrf_score_orders_by_chunk_id_ascending(self) -> None:
        dense = (_make_result("chunk-b"),)
        sparse = (_make_result("chunk-a"),)
        fused = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=sparse,
            rrf_k=RRF_K,
        )

        assert fused[0].chunk.chunk_id == ChunkId("chunk-a")
        assert fused[1].chunk.chunk_id == ChunkId("chunk-b")
        assert fused[0].score == pytest.approx(fused[1].score)

    def test_chunk_payload_from_best_ranked_occurrence(self) -> None:
        dense = (_make_result("chunk-shared", text="dense payload"),)
        sparse = (
            _make_result("chunk-other"),
            _make_result("chunk-shared", text="sparse payload"),
        )
        fused = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=sparse,
            rrf_k=RRF_K,
        )

        shared = next(r for r in fused if r.chunk.chunk_id == ChunkId("chunk-shared"))
        assert shared.chunk.text == "dense payload"

    def test_dense_wins_chunk_payload_on_equal_rank_tie(self) -> None:
        dense = (_make_result("chunk-shared", text="dense wins"),)
        sparse = (_make_result("chunk-shared", text="sparse loses"),)
        fused = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=sparse,
            rrf_k=RRF_K,
        )

        assert fused[0].chunk.text == "dense wins"

    def test_custom_rrf_k_changes_scores_predictably(self) -> None:
        dense = (_make_result("chunk-a"),)
        fused_default = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=(),
            rrf_k=60,
        )
        fused_custom = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=(),
            rrf_k=10,
        )

        assert fused_default[0].score == pytest.approx(1.0 / 61)
        assert fused_custom[0].score == pytest.approx(1.0 / 11)
        assert fused_custom[0].score > fused_default[0].score

    def test_output_sorted_descending_by_fused_score(self) -> None:
        dense = (
            _make_result("chunk-low"),
            _make_result("chunk-high"),
        )
        sparse = (
            _make_result("chunk-high"),
            _make_result("chunk-low"),
        )
        fused = reciprocal_rank_fusion(
            dense_results=dense,
            sparse_results=sparse,
            rrf_k=RRF_K,
        )

        scores = [result.score for result in fused]
        assert scores == sorted(scores, reverse=True)
        assert fused[0].chunk.chunk_id == ChunkId("chunk-high")


class TestFusionRetriever:
    def test_calls_each_leaf_retriever_once(self) -> None:
        dense = MagicMock()
        sparse = MagicMock()
        query = SearchQuery(text="fusion query", top_k=3)
        leaf_query = SearchQuery(text=query.text, top_k=6)
        empty = RetrievalResult(query=leaf_query, results=())
        dense.retrieve.return_value = empty
        sparse.retrieve.return_value = empty
        retriever = FusionRetriever(
            dense_retriever=dense,
            sparse_retriever=sparse,
            settings=FusionRetrievalSettings(),
        )

        retriever.retrieve(query)

        dense.retrieve.assert_called_once()
        sparse.retrieve.assert_called_once()

    def test_forwards_expanded_leaf_top_k_to_leaf_retrievers(self) -> None:
        dense = MagicMock()
        sparse = MagicMock()
        query = SearchQuery(text="expanded pool", top_k=4)
        expected_leaf_query = SearchQuery(text=query.text, top_k=8)
        empty = RetrievalResult(query=expected_leaf_query, results=())
        dense.retrieve.return_value = empty
        sparse.retrieve.return_value = empty
        retriever = FusionRetriever(
            dense_retriever=dense,
            sparse_retriever=sparse,
            settings=FusionRetrievalSettings(leaf_top_k_multiplier=2),
        )

        retriever.retrieve(query)

        dense.retrieve.assert_called_once_with(expected_leaf_query)
        sparse.retrieve.assert_called_once_with(expected_leaf_query)

    def test_returns_caller_query_not_leaf_query(self) -> None:
        dense = MagicMock()
        sparse = MagicMock()
        query = SearchQuery(text="caller query", top_k=2)
        leaf_query = SearchQuery(text=query.text, top_k=4)
        empty = RetrievalResult(query=leaf_query, results=())
        dense.retrieve.return_value = empty
        sparse.retrieve.return_value = empty
        retriever = FusionRetriever(
            dense_retriever=dense,
            sparse_retriever=sparse,
            settings=FusionRetrievalSettings(),
        )

        result = retriever.retrieve(query)

        assert result.query is query

    def test_truncates_to_caller_top_k(self) -> None:
        dense = MagicMock()
        sparse = MagicMock()
        query = SearchQuery(text="truncate", top_k=2)
        leaf_query = SearchQuery(text=query.text, top_k=4)
        dense_results = tuple(_make_result(f"dense-{index}") for index in range(3))
        sparse_results = tuple(_make_result(f"sparse-{index}") for index in range(3))
        dense.retrieve.return_value = RetrievalResult(
            query=leaf_query,
            results=dense_results,
        )
        sparse.retrieve.return_value = RetrievalResult(
            query=leaf_query,
            results=sparse_results,
        )
        retriever = FusionRetriever(
            dense_retriever=dense,
            sparse_retriever=sparse,
            settings=FusionRetrievalSettings(),
        )

        result = retriever.retrieve(query)

        assert len(result.results) <= query.top_k

    def test_propagates_leaf_retriever_exceptions(self) -> None:
        dense = MagicMock()
        sparse = MagicMock()
        dense.retrieve.side_effect = RuntimeError("dense failure")
        retriever = FusionRetriever(
            dense_retriever=dense,
            sparse_retriever=sparse,
            settings=FusionRetrievalSettings(),
        )
        query = SearchQuery(text="error path", top_k=3)

        with pytest.raises(RuntimeError, match="dense failure"):
            retriever.retrieve(query)

        sparse.retrieve.assert_not_called()

    def test_empty_leaf_results_return_valid_fused_output(self) -> None:
        dense = MagicMock()
        sparse = MagicMock()
        query = SearchQuery(text="empty leaves", top_k=3)
        leaf_query = SearchQuery(text=query.text, top_k=6)
        empty = RetrievalResult(query=leaf_query, results=())
        dense.retrieve.return_value = empty
        sparse.retrieve.return_value = empty
        retriever = FusionRetriever(
            dense_retriever=dense,
            sparse_retriever=sparse,
            settings=FusionRetrievalSettings(),
        )

        result = retriever.retrieve(query)

        assert result.query is query
        assert result.results == ()
