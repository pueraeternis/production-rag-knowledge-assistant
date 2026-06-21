"""Tier 1 MCP knowledge handler functions."""

from knowledge_assistant.core.retrieval import SearchQuery
from knowledge_assistant.indexing.pipeline import IndexingPipeline
from knowledge_assistant.mcp_server.config import McpServerSettings
from knowledge_assistant.mcp_server.exceptions import ApprovalRequiredError
from knowledge_assistant.mcp_server.formatting import (
    format_index_documents_apply_response,
    format_index_documents_preview_response,
    format_search_documents_response,
    indexing_sources_from_schemas,
)
from knowledge_assistant.mcp_server.schemas import (
    IndexDocumentsApplyRequest,
    IndexDocumentsApplyResponse,
    IndexDocumentsPreviewRequest,
    IndexDocumentsPreviewResponse,
    SearchDocumentsRequest,
    SearchDocumentsResponse,
)
from knowledge_assistant.retrieval.protocol import Retriever


def search_documents(
    request: SearchDocumentsRequest,
    *,
    retriever: Retriever,
    settings: McpServerSettings,
) -> SearchDocumentsResponse:
    """
    Retrieve ranked chunks for grounding.

    Returns retrieval evidence with source attribution. Does not generate answers.
    When production wiring uses ``RerankRetriever``, ``score`` values are reranker
    relevance scores and are not comparable to dense, sparse, or RRF scores.
    """
    top_k = request.top_k if request.top_k is not None else settings.default_top_k
    query = SearchQuery(text=request.query, top_k=top_k)
    retrieval_result = retriever.retrieve(query)
    return format_search_documents_response(
        query=request.query,
        top_k=top_k,
        results=retrieval_result.results,
    )


def index_documents_preview(
    request: IndexDocumentsPreviewRequest,
    *,
    pipeline: IndexingPipeline,
) -> IndexDocumentsPreviewResponse:
    """Preview indexing impact without mutating storage."""
    sources = indexing_sources_from_schemas(request.sources)
    preview = pipeline.preview_indexing(sources)
    return format_index_documents_preview_response(preview)


def index_documents_apply(
    request: IndexDocumentsApplyRequest,
    *,
    pipeline: IndexingPipeline,
) -> IndexDocumentsApplyResponse:
    """
    Apply indexing after explicit human approval.

    Requires ``approval_confirmed=True``. Does not prompt interactively.
    """
    if request.approval_confirmed is not True:
        raise ApprovalRequiredError

    sources = indexing_sources_from_schemas(request.sources)
    result = pipeline.index_documents(sources, rebuild=request.rebuild)
    return format_index_documents_apply_response(result)
