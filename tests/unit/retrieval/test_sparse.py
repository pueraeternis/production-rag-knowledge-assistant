"""Unit tests for SparseRetriever."""

import inspect
from unittest.mock import MagicMock

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.retrieval.sparse import SparseRetriever
from knowledge_assistant.retrieval.sparse_vectors import SparseQueryVector


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


class TestSparseRetriever:
    def test_retrieve_calls_embed_query_with_query_text(self) -> None:
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = SparseQueryVector(
            indices=(1,),
            values=(1.0,),
        )
        vector_store = MagicMock()
        vector_store.search_sparse.return_value = ()
        retriever = SparseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )
        query = SearchQuery(text="what is sparse retrieval?", top_k=3)

        retriever.retrieve(query)

        embedding_provider.embed_query.assert_called_once_with(query.text)

    def test_retrieve_calls_search_sparse_with_indices_values_and_top_k(self) -> None:
        sparse_vector = SparseQueryVector(indices=(10, 20), values=(0.7, 0.3))
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = sparse_vector
        vector_store = MagicMock()
        vector_store.search_sparse.return_value = ()
        retriever = SparseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )
        query = SearchQuery(text="search query", top_k=5)

        retriever.retrieve(query)

        vector_store.search_sparse.assert_called_once_with(
            indices=(10, 20),
            values=(0.7, 0.3),
            top_k=5,
        )

    def test_retrieve_returns_retrieval_result_with_echoed_query(self) -> None:
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = SparseQueryVector(
            indices=(1,),
            values=(1.0,),
        )
        vector_store = MagicMock()
        vector_store.search_sparse.return_value = ()
        retriever = SparseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )
        query = SearchQuery(text="echo query", top_k=2)

        result = retriever.retrieve(query)

        assert isinstance(result, RetrievalResult)
        assert result.query == query
        assert result.results == ()

    def test_empty_search_results_return_valid_retrieval_result(self) -> None:
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = SparseQueryVector(
            indices=(1,),
            values=(1.0,),
        )
        vector_store = MagicMock()
        vector_store.search_sparse.return_value = ()
        retriever = SparseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
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
        embedding_provider.embed_query.return_value = SparseQueryVector(
            indices=(1,),
            values=(1.0,),
        )
        vector_store = MagicMock()
        vector_store.search_sparse.return_value = expected_results
        retriever = SparseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )
        query = SearchQuery(text="ranked query", top_k=2)

        result = retriever.retrieve(query)

        assert result.results == expected_results
        assert result.results[0].score == 0.95
        assert result.results[1].score == 0.85

    def test_top_k_forwarded_to_search_sparse(self) -> None:
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = SparseQueryVector(
            indices=(1,),
            values=(1.0,),
        )
        vector_store = MagicMock()
        vector_store.search_sparse.return_value = ()
        retriever = SparseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )
        query = SearchQuery(text="top k query", top_k=7)

        retriever.retrieve(query)

        vector_store.search_sparse.assert_called_once()
        assert vector_store.search_sparse.call_args.kwargs["top_k"] == 7

    def test_defensive_slice_when_storage_returns_excess_results(self) -> None:
        excess_results = tuple(
            _make_search_result(f"chunk-{index}", score=0.9 - index * 0.1)
            for index in range(3)
        )
        embedding_provider = MagicMock()
        embedding_provider.embed_query.return_value = SparseQueryVector(
            indices=(1,),
            values=(1.0,),
        )
        vector_store = MagicMock()
        vector_store.search_sparse.return_value = excess_results
        retriever = SparseRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )
        query = SearchQuery(text="slice query", top_k=2)

        result = retriever.retrieve(query)

        assert len(result.results) == 2
        assert result.results == excess_results[:2]

    def test_retrieve_does_not_expose_vector_accepting_api(self) -> None:
        assert not hasattr(SparseRetriever, "search_sparse")
        signature = inspect.signature(SparseRetriever.retrieve)
        assert tuple(signature.parameters) == ("self", "query")
