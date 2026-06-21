"""Unit tests for search_documents handler."""

from unittest.mock import MagicMock

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.mcp_server.config import McpServerSettings
from knowledge_assistant.mcp_server.schemas import SearchDocumentsRequest
from knowledge_assistant.mcp_server.tools import search_documents


def _make_search_result() -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=ChunkId("chunk-1"),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Overview",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text="retrieved chunk text",
        ),
        score=0.91,
        source=SourceReference(
            document_title="Guide",
            document_path="docs/guide.md",
            section_title="Overview",
            line_range=LineRange(start_line=1, end_line=5),
        ),
    )


class TestSearchDocuments:
    def test_calls_retriever_with_search_query(self) -> None:
        retriever = MagicMock()
        retriever.retrieve.return_value = RetrievalResult(
            query=SearchQuery(text="python retrieval", top_k=5),
            results=(_make_search_result(),),
        )
        request = SearchDocumentsRequest(query="python retrieval")

        response = search_documents(
            request,
            retriever=retriever,
            settings=McpServerSettings(default_top_k=5),
        )

        retriever.retrieve.assert_called_once()
        called_query = retriever.retrieve.call_args.args[0]
        assert isinstance(called_query, SearchQuery)
        assert called_query.text == "python retrieval"
        assert called_query.top_k == 5
        assert response.query == "python retrieval"
        assert response.top_k == 5
        assert len(response.hits) == 1
        assert response.hits[0].chunk_id == "chunk-1"
        assert response.hits[0].source.document_path == "docs/guide.md"

    def test_uses_request_top_k_when_provided(self) -> None:
        retriever = MagicMock()
        retriever.retrieve.return_value = RetrievalResult(
            query=SearchQuery(text="query", top_k=2),
            results=(),
        )
        request = SearchDocumentsRequest(query="query", top_k=2)

        response = search_documents(
            request,
            retriever=retriever,
            settings=McpServerSettings(default_top_k=10),
        )

        called_query = retriever.retrieve.call_args.args[0]
        assert called_query.top_k == 2
        assert response.top_k == 2

    def test_returns_empty_hits_without_generating_answer(self) -> None:
        retriever = MagicMock()
        retriever.retrieve.return_value = RetrievalResult(
            query=SearchQuery(text="query", top_k=3),
            results=(),
        )
        request = SearchDocumentsRequest(query="query")

        response = search_documents(
            request,
            retriever=retriever,
            settings=McpServerSettings(),
        )

        assert response.hits == ()
