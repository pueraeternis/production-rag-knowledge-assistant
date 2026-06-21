"""Unit tests for retrieval domain models."""

from dataclasses import FrozenInstanceError

import pytest

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.core.source import LineRange, SourceReference


def _make_source() -> SourceReference:
    return SourceReference(
        document_title="Guide",
        document_path="docs/guide.md",
        section_title="Section",
        line_range=LineRange(start_line=1, end_line=5),
    )


def _make_chunk(chunk_id: str = "chunk-1", text: str = "chunk text") -> Chunk:
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


class TestSearchQuery:
    def test_valid_construction(self) -> None:
        query = SearchQuery(text="hybrid retrieval", top_k=5)
        assert query.text == "hybrid retrieval"
        assert query.top_k == 5

    def test_text_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="text must be non-empty"):
            SearchQuery(text="   ", top_k=5)

    @pytest.mark.parametrize("top_k", [0, -1])
    def test_top_k_must_be_at_least_one(self, top_k: int) -> None:
        with pytest.raises(ValueError, match="top_k must be >= 1"):
            SearchQuery(text="query", top_k=top_k)

    def test_immutability(self) -> None:
        query = SearchQuery(text="query", top_k=3)
        with pytest.raises(FrozenInstanceError):
            query.top_k = 5  # type: ignore[misc]


class TestSearchResult:
    def test_valid_construction(self) -> None:
        chunk = _make_chunk()
        result = SearchResult(chunk=chunk, score=0.95, source=_make_source())
        assert result.chunk == chunk
        assert result.score == 0.95

    def test_immutability(self) -> None:
        result = SearchResult(chunk=_make_chunk(), score=0.5, source=_make_source())
        with pytest.raises(FrozenInstanceError):
            result.score = 0.9  # type: ignore[misc]


class TestRetrievalResult:
    def test_valid_construction_with_results(self) -> None:
        query = SearchQuery(text="query", top_k=2)
        results = (
            SearchResult(
                chunk=_make_chunk("chunk-1"), score=0.9, source=_make_source()
            ),
            SearchResult(
                chunk=_make_chunk("chunk-2"), score=0.8, source=_make_source()
            ),
        )
        retrieval = RetrievalResult(query=query, results=results)
        assert retrieval.query == query
        assert retrieval.results == results

    def test_valid_empty_results(self) -> None:
        query = SearchQuery(text="query", top_k=5)
        retrieval = RetrievalResult(query=query, results=())
        assert retrieval.results == ()

    def test_results_length_must_not_exceed_top_k(self) -> None:
        query = SearchQuery(text="query", top_k=1)
        results = (
            SearchResult(
                chunk=_make_chunk("chunk-1"), score=0.9, source=_make_source()
            ),
            SearchResult(
                chunk=_make_chunk("chunk-2"), score=0.8, source=_make_source()
            ),
        )
        with pytest.raises(ValueError, match=r"results length must be <= query.top_k"):
            RetrievalResult(query=query, results=results)

    def test_immutability(self) -> None:
        query = SearchQuery(text="query", top_k=1)
        retrieval = RetrievalResult(query=query, results=())
        with pytest.raises(FrozenInstanceError):
            retrieval.results = ()  # type: ignore[misc]
