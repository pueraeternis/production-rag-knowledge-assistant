"""Unit tests for RerankRetriever orchestration."""

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
from knowledge_assistant.retrieval.config import RerankRetrievalSettings
from knowledge_assistant.retrieval.rerank import RerankRetriever, StubReranker


def _make_source() -> SourceReference:
    return SourceReference(
        document_title="Guide",
        document_path="docs/guide.md",
        section_title="Section",
        line_range=LineRange(start_line=1, end_line=5),
    )


def _make_result(chunk_id: str, score: float, *, text: str) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=ChunkId(chunk_id),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Section",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text=text,
        ),
        score=score,
        source=_make_source(),
    )


class TestRerankRetriever:
    def test_calls_base_retriever_once(self) -> None:
        base = MagicMock()
        query = SearchQuery(text="orchestration", top_k=3)
        candidate_query = SearchQuery(text=query.text, top_k=6)
        base.retrieve.return_value = RetrievalResult(query=candidate_query, results=())
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(),
        )

        retriever.retrieve(query)

        base.retrieve.assert_called_once()

    def test_forwards_expanded_candidate_top_k(self) -> None:
        base = MagicMock()
        query = SearchQuery(text="expanded pool", top_k=4)
        expected_candidate_query = SearchQuery(text=query.text, top_k=8)
        base.retrieve.return_value = RetrievalResult(
            query=expected_candidate_query,
            results=(),
        )
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(candidate_top_k_multiplier=2),
        )

        retriever.retrieve(query)

        base.retrieve.assert_called_once_with(expected_candidate_query)

    def test_passes_caller_query_to_reranker(self) -> None:
        base = MagicMock()
        reranker = MagicMock()
        query = SearchQuery(text="caller query", top_k=2)
        candidate_query = SearchQuery(text=query.text, top_k=4)
        candidates = (
            _make_result("chunk-a", 0.5, text="caller query alpha"),
            _make_result("chunk-b", 0.4, text="caller query beta"),
        )
        base.retrieve.return_value = RetrievalResult(
            query=candidate_query,
            results=candidates,
        )
        reranker.rerank.return_value = candidates
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=reranker,
            settings=RerankRetrievalSettings(),
        )

        retriever.retrieve(query)

        reranker.rerank.assert_called_once_with(query=query, candidates=candidates)

    def test_returns_caller_query(self) -> None:
        base = MagicMock()
        query = SearchQuery(text="echo query", top_k=2)
        candidate_query = SearchQuery(text=query.text, top_k=4)
        base.retrieve.return_value = RetrievalResult(query=candidate_query, results=())
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(),
        )

        result = retriever.retrieve(query)

        assert result.query is query

    def test_truncates_to_caller_top_k(self) -> None:
        base = MagicMock()
        query = SearchQuery(text="truncate", top_k=2)
        candidate_query = SearchQuery(text=query.text, top_k=4)
        candidates = tuple(
            _make_result(f"chunk-{index}", 0.1 * index, text=f"truncate token {index}")
            for index in range(4)
        )
        base.retrieve.return_value = RetrievalResult(
            query=candidate_query,
            results=candidates,
        )
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(),
        )

        result = retriever.retrieve(query)

        assert len(result.results) <= query.top_k

    def test_raises_value_error_when_reranker_drops_candidates(self) -> None:
        base = MagicMock()
        reranker = MagicMock()
        query = SearchQuery(text="contract violation", top_k=2)
        candidate_query = SearchQuery(text=query.text, top_k=4)
        candidates = (
            _make_result("chunk-a", 0.5, text="contract violation alpha"),
            _make_result("chunk-b", 0.4, text="contract violation beta"),
        )
        base.retrieve.return_value = RetrievalResult(
            query=candidate_query,
            results=candidates,
        )
        reranker.rerank.return_value = (candidates[0],)
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=reranker,
            settings=RerankRetrievalSettings(),
        )

        with pytest.raises(
            ValueError,
            match="reranker must return 2 candidates, got 1",
        ):
            retriever.retrieve(query)

    def test_raises_value_error_when_reranker_adds_candidates(self) -> None:
        base = MagicMock()
        reranker = MagicMock()
        query = SearchQuery(text="extra candidate", top_k=2)
        candidate_query = SearchQuery(text=query.text, top_k=4)
        candidates = (_make_result("chunk-a", 0.5, text="extra candidate alpha"),)
        extra = _make_result("chunk-b", 0.4, text="extra candidate beta")
        base.retrieve.return_value = RetrievalResult(
            query=candidate_query,
            results=candidates,
        )
        reranker.rerank.return_value = (candidates[0], extra)
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=reranker,
            settings=RerankRetrievalSettings(),
        )

        with pytest.raises(
            ValueError,
            match="reranker must return 1 candidates, got 2",
        ):
            retriever.retrieve(query)

    def test_reranker_scores_replace_previous_scores(self) -> None:
        base = MagicMock()
        query = SearchQuery(text="python retrieval", top_k=2)
        candidate_query = SearchQuery(text=query.text, top_k=4)
        candidates = (
            _make_result("chunk-low", 0.99, text="unrelated"),
            _make_result("chunk-high", 0.01, text="python retrieval guide"),
        )
        base.retrieve.return_value = RetrievalResult(
            query=candidate_query,
            results=candidates,
        )
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(),
        )

        result = retriever.retrieve(query)

        assert result.results[0].chunk.chunk_id == ChunkId("chunk-high")
        assert result.results[0].score != 0.01

    def test_propagates_base_retriever_exceptions(self) -> None:
        base = MagicMock()
        base.retrieve.side_effect = RuntimeError("base failure")
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(),
        )
        query = SearchQuery(text="error path", top_k=3)

        with pytest.raises(RuntimeError, match="base failure"):
            retriever.retrieve(query)

    def test_propagates_reranker_exceptions(self) -> None:
        base = MagicMock()
        reranker = MagicMock()
        query = SearchQuery(text="reranker error", top_k=2)
        candidate_query = SearchQuery(text=query.text, top_k=4)
        candidates = (_make_result("chunk-a", 0.5, text="reranker error alpha"),)
        base.retrieve.return_value = RetrievalResult(
            query=candidate_query,
            results=candidates,
        )
        reranker.rerank.side_effect = RuntimeError("reranker failure")
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=reranker,
            settings=RerankRetrievalSettings(),
        )

        with pytest.raises(RuntimeError, match="reranker failure"):
            retriever.retrieve(query)

    def test_empty_base_results_skip_reranker(self) -> None:
        base = MagicMock()
        reranker = MagicMock()
        query = SearchQuery(text="empty base", top_k=3)
        candidate_query = SearchQuery(text=query.text, top_k=6)
        base.retrieve.return_value = RetrievalResult(query=candidate_query, results=())
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=reranker,
            settings=RerankRetrievalSettings(),
        )

        result = retriever.retrieve(query)

        reranker.rerank.assert_not_called()
        assert result.query is query
        assert result.results == ()

    def test_fewer_base_candidates_than_requested(self) -> None:
        base = MagicMock()
        query = SearchQuery(text="short list", top_k=5)
        candidate_query = SearchQuery(text=query.text, top_k=10)
        candidates = (
            _make_result("chunk-a", 0.5, text="short list alpha"),
            _make_result("chunk-b", 0.4, text="short list beta"),
        )
        base.retrieve.return_value = RetrievalResult(
            query=candidate_query,
            results=candidates,
        )
        retriever = RerankRetriever(
            base_retriever=base,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(),
        )

        result = retriever.retrieve(query)

        assert len(result.results) == len(candidates)
        assert len(result.results) <= query.top_k
