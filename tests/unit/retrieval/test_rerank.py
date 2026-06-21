"""Unit tests for reranking settings and StubReranker."""

import pytest

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import SearchQuery, SearchResult
from knowledge_assistant.core.source import LineRange
from knowledge_assistant.retrieval.config import RerankRetrievalSettings
from knowledge_assistant.retrieval.rerank import StubReranker, stub_rerank_score


def _make_chunk(chunk_id: str, text: str) -> Chunk:
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
    score: float,
    *,
    text: str | None = None,
) -> SearchResult:
    return SearchResult(
        chunk=_make_chunk(
            chunk_id,
            text if text is not None else f"text for {chunk_id}",
        ),
        score=score,
    )


class TestRerankRetrievalSettings:
    def test_default_candidate_top_k_multiplier(self) -> None:
        settings = RerankRetrievalSettings()
        assert settings.candidate_top_k_multiplier == 2

    def test_resolve_candidate_top_k(self) -> None:
        settings = RerankRetrievalSettings()
        assert settings.resolve_candidate_top_k(5) == 10

    @pytest.mark.parametrize("candidate_top_k_multiplier", [0, -1])
    def test_candidate_top_k_multiplier_must_be_at_least_one(
        self,
        candidate_top_k_multiplier: int,
    ) -> None:
        with pytest.raises(ValueError, match="candidate_top_k_multiplier must be >= 1"):
            RerankRetrievalSettings(
                candidate_top_k_multiplier=candidate_top_k_multiplier,
            )


class TestStubReranker:
    def test_empty_candidates_returns_empty_tuple(self) -> None:
        query = SearchQuery(text="empty candidates", top_k=3)
        reranker = StubReranker()

        assert reranker.rerank(query, ()) == ()

    def test_preserves_candidate_count(self) -> None:
        query = SearchQuery(text="python retrieval", top_k=2)
        candidates = (
            _make_result("chunk-a", 0.9, text="python guide"),
            _make_result("chunk-b", 0.1, text="unrelated topic"),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert len(reranked) == len(candidates)

    def test_deterministic_scores_for_same_inputs(self) -> None:
        query = SearchQuery(text="hybrid search fusion", top_k=3)
        candidates = (
            _make_result("chunk-a", 0.5, text="hybrid search overview"),
            _make_result("chunk-b", 0.8, text="fusion retrieval notes"),
        )
        reranker = StubReranker()

        first = reranker.rerank(query, candidates)
        second = reranker.rerank(query, candidates)

        assert first == second

    def test_higher_overlap_candidate_sorts_first(self) -> None:
        query = SearchQuery(text="python retrieval", top_k=2)
        candidates = (
            _make_result("chunk-low", 0.99, text="unrelated content"),
            _make_result("chunk-high", 0.01, text="python retrieval guide"),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert reranked[0].chunk.chunk_id == ChunkId("chunk-high")
        assert reranked[0].score > reranked[1].score

    def test_reranked_score_replaces_input_score(self) -> None:
        query = SearchQuery(text="python", top_k=1)
        prior_score = 0.42
        candidates = (_make_result("chunk-a", prior_score, text="python basics"),)
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert reranked[0].score == pytest.approx(
            stub_rerank_score("python", "python basics"),
        )
        assert reranked[0].score != prior_score

    def test_tie_on_reranker_score_orders_by_chunk_id_ascending(self) -> None:
        query = SearchQuery(text="shared overlap", top_k=3)
        shared_text = "shared overlap text"
        candidates = (
            _make_result("chunk-b", 0.5, text=shared_text),
            _make_result("chunk-a", 0.5, text=shared_text),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert reranked[0].chunk.chunk_id == ChunkId("chunk-a")
        assert reranked[1].chunk.chunk_id == ChunkId("chunk-b")
        assert reranked[0].score == pytest.approx(reranked[1].score)

    def test_every_chunk_id_appears_exactly_once(self) -> None:
        query = SearchQuery(text="token overlap", top_k=3)
        candidates = (
            _make_result("chunk-a", 0.1, text="token overlap alpha"),
            _make_result("chunk-b", 0.2, text="token overlap beta"),
            _make_result("chunk-c", 0.3, text="token overlap gamma"),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)
        input_ids = {candidate.chunk.chunk_id for candidate in candidates}
        output_ids = [result.chunk.chunk_id for result in reranked]

        assert len(output_ids) == len(set(output_ids))
        assert set(output_ids) == input_ids

    def test_chunk_payloads_unchanged(self) -> None:
        query = SearchQuery(text="preserve payload", top_k=2)
        candidates = (
            _make_result("chunk-a", 0.5, text="preserve payload alpha"),
            _make_result("chunk-b", 0.4, text="preserve payload beta"),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        for original in candidates:
            matching = next(
                result
                for result in reranked
                if result.chunk.chunk_id == original.chunk.chunk_id
            )
            assert matching.chunk == original.chunk

    def test_tokenization_ignores_trailing_punctuation(self) -> None:
        query = SearchQuery(text="python retrieval", top_k=2)
        candidates = (
            _make_result("chunk-plain", 0.1, text="python retrieval guide"),
            _make_result("chunk-punct", 0.9, text="python retrieval, guide"),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert reranked[0].score == pytest.approx(reranked[1].score)
        assert stub_rerank_score(
            "python retrieval", "python retrieval,"
        ) == pytest.approx(
            stub_rerank_score("python retrieval", "python retrieval"),
        )
