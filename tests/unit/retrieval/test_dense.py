"""Unit tests for DenseRetriever."""

import inspect
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
from knowledge_assistant.retrieval.config import DenseRetrievalSettings
from knowledge_assistant.retrieval.dense import DenseRetriever
from knowledge_assistant.retrieval.exceptions import EmbeddingDimensionError


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


def _make_search_result(
    chunk_id: str = "chunk-1",
    score: float = 0.9,
) -> SearchResult:
    return SearchResult(
        chunk=_make_chunk(chunk_id),
        score=score,
        source=_make_source(),
    )


class TestDenseRetriever:
    def test_retrieve_calls_embed_query_with_query_text(self) -> None:
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = (0.1,) * 8
        vector_store = MagicMock()
        vector_store.search_dense.return_value = ()
        retriever = DenseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="what is hybrid retrieval?", top_k=3)

        retriever.retrieve(query)

        embedding_provider.embed_query.assert_called_once_with(query.text)

    def test_retrieve_calls_search_dense_with_vector_and_top_k(self) -> None:
        vector = (0.25, 0.5, 0.75, 1.0, 0.0, 0.1, 0.2, 0.3)
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = vector
        vector_store = MagicMock()
        vector_store.search_dense.return_value = ()
        retriever = DenseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="search query", top_k=5)

        retriever.retrieve(query)

        vector_store.search_dense.assert_called_once_with(vector=vector, top_k=5)

    def test_dimension_mismatch_raises_before_search_dense(self) -> None:
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = (0.1,) * 4
        vector_store = MagicMock()
        retriever = DenseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="query", top_k=3)

        with pytest.raises(EmbeddingDimensionError, match="does not match expected 8"):
            retriever.retrieve(query)

        vector_store.search_dense.assert_not_called()

    def test_retrieve_returns_retrieval_result_with_echoed_query(self) -> None:
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = (0.1,) * 8
        vector_store = MagicMock()
        vector_store.search_dense.return_value = ()
        retriever = DenseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="echo query", top_k=2)

        result = retriever.retrieve(query)

        assert isinstance(result, RetrievalResult)
        assert result.query == query
        assert result.results == ()

    def test_empty_search_results_return_valid_retrieval_result(self) -> None:
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = (0.1,) * 8
        vector_store = MagicMock()
        vector_store.search_dense.return_value = ()
        retriever = DenseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="empty results", top_k=3)

        result = retriever.retrieve(query)

        assert result.results == ()

    def test_non_empty_results_propagated_unchanged_in_order(self) -> None:
        expected_results = (
            _make_search_result("chunk-1", score=0.95),
            _make_search_result("chunk-2", score=0.85),
        )
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = (0.1,) * 8
        vector_store = MagicMock()
        vector_store.search_dense.return_value = expected_results
        retriever = DenseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="ranked query", top_k=2)

        result = retriever.retrieve(query)

        assert result.results == expected_results
        assert result.results[0].score == 0.95
        assert result.results[1].score == 0.85

    def test_top_k_forwarded_to_search_dense(self) -> None:
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = (0.1,) * 8
        vector_store = MagicMock()
        vector_store.search_dense.return_value = ()
        retriever = DenseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="top k query", top_k=7)

        retriever.retrieve(query)

        vector_store.search_dense.assert_called_once()
        assert vector_store.search_dense.call_args.kwargs["top_k"] == 7

    def test_defensive_slice_when_storage_returns_excess_results(self) -> None:
        excess_results = tuple(
            _make_search_result(f"chunk-{index}", score=0.9 - index * 0.1)
            for index in range(3)
        )
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = (0.1,) * 8
        vector_store = MagicMock()
        vector_store.search_dense.return_value = excess_results
        retriever = DenseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="slice query", top_k=2)

        result = retriever.retrieve(query)

        assert len(result.results) == 2
        assert result.results == excess_results[:2]

    def test_retrieve_does_not_expose_vector_accepting_api(self) -> None:
        assert not hasattr(DenseRetriever, "search_dense")
        signature = inspect.signature(DenseRetriever.retrieve)
        assert tuple(signature.parameters) == ("self", "query")
