"""Integration tests for MCP handler flows with fake dependencies."""

from typing import cast

from mcp_handler_fakes import (
    FakeIndexingPipeline,
    FakeRetriever,
    make_index_result,
    make_preview,
    make_search_result,
)

from knowledge_assistant.core.indexing import IndexingSourceKind
from knowledge_assistant.core.retrieval import RetrievalResult, SearchQuery
from knowledge_assistant.indexing.pipeline import IndexingPipeline
from knowledge_assistant.mcp_server.config import McpServerSettings
from knowledge_assistant.mcp_server.exceptions import ApprovalRequiredError
from knowledge_assistant.mcp_server.schemas import (
    IndexDocumentsApplyRequest,
    IndexDocumentsPreviewRequest,
    IndexingSourceSchema,
    SearchDocumentsRequest,
)
from knowledge_assistant.mcp_server.tools import (
    index_documents_apply,
    index_documents_preview,
    search_documents,
)


class TestHandlerIntegration:
    def test_search_documents_end_to_end_with_fake_retriever(self) -> None:
        query = SearchQuery(text="integration query", top_k=3)
        retriever = FakeRetriever(
            return_value=RetrievalResult(query=query, results=(make_search_result(),)),
        )
        request = SearchDocumentsRequest(query="integration query", top_k=3)

        response = search_documents(
            request,
            retriever=retriever,
            settings=McpServerSettings(),
        )

        assert retriever.last_query == query
        assert response.top_k == 3
        assert response.hits[0].text == "integration chunk text"
        assert response.hits[0].source.document_title == "Guide"

    def test_index_documents_preview_end_to_end(self) -> None:
        pipeline = FakeIndexingPipeline(preview_return=make_preview())
        request = IndexDocumentsPreviewRequest(
            sources=(
                IndexingSourceSchema(
                    kind="directory",
                    location="docs",
                    recursive=True,
                ),
            ),
        )

        response = index_documents_preview(
            request,
            pipeline=cast("IndexingPipeline", pipeline),
        )

        assert pipeline.preview_call_count == 1
        assert pipeline.index_call_count == 0
        assert pipeline.last_sources is not None
        assert pipeline.last_sources[0].kind is IndexingSourceKind.DIRECTORY
        assert response.replaces_existing is True

    def test_index_documents_apply_requires_approval(self) -> None:
        pipeline = FakeIndexingPipeline(index_return=make_index_result())
        request = IndexDocumentsApplyRequest(
            sources=(
                IndexingSourceSchema(
                    kind="directory",
                    location="docs",
                    recursive=True,
                ),
            ),
            approval_confirmed=False,
        )

        try:
            index_documents_apply(
                request,
                pipeline=cast("IndexingPipeline", pipeline),
            )
        except ApprovalRequiredError:
            pass
        else:
            raise AssertionError("expected ApprovalRequiredError")

        assert pipeline.index_call_count == 0

    def test_index_documents_apply_end_to_end_when_approved(self) -> None:
        pipeline = FakeIndexingPipeline(index_return=make_index_result())
        request = IndexDocumentsApplyRequest(
            sources=(
                IndexingSourceSchema(
                    kind="directory",
                    location="docs",
                    recursive=True,
                ),
            ),
            approval_confirmed=True,
        )

        response = index_documents_apply(
            request,
            pipeline=cast("IndexingPipeline", pipeline),
        )

        assert pipeline.index_call_count == 1
        assert response.upserted_count == 6
