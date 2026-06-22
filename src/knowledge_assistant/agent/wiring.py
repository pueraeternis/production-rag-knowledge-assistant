"""Wiring helpers for concrete MCP tool adapters and registry construction."""

from __future__ import annotations

from knowledge_assistant.agent.tools import (
    INDEX_DOCUMENTS_APPLY_PARAMETERS,
    INDEX_DOCUMENTS_PREVIEW_PARAMETERS,
    SEARCH_DOCUMENTS_PARAMETERS,
    ToolRegistry,
)
from knowledge_assistant.indexing.pipeline import IndexingPipeline
from knowledge_assistant.llm.messages import ToolDefinition
from knowledge_assistant.mcp_server.config import McpServerSettings
from knowledge_assistant.mcp_server.schemas import (
    IndexDocumentsApplyRequest,
    IndexDocumentsPreviewRequest,
    SearchDocumentsRequest,
)
from knowledge_assistant.mcp_server.tools import (
    index_documents_apply,
    index_documents_preview,
    search_documents,
)
from knowledge_assistant.retrieval.protocol import Retriever


class SearchDocumentsTool:
    """Adapter for the search_documents MCP handler."""

    def __init__(
        self,
        *,
        retriever: Retriever,
        settings: McpServerSettings,
    ) -> None:
        self._retriever = retriever
        self._settings = settings

    @property
    def name(self) -> str:
        return "search_documents"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Search the internal documentation corpus only. Use for questions "
                "about company policies, procedures, engineering docs, HR, finance, "
                "and product knowledge. Do not use for general knowledge or off-topic "
                "questions unrelated to the corpus."
            ),
            parameters=SEARCH_DOCUMENTS_PARAMETERS,
        )

    def execute(self, arguments: dict[str, object]) -> str:
        request = SearchDocumentsRequest.model_validate(arguments)
        response = search_documents(
            request,
            retriever=self._retriever,
            settings=self._settings,
        )
        return response.model_dump_json()


class IndexDocumentsPreviewTool:
    """Adapter for the index_documents_preview MCP handler."""

    def __init__(self, *, pipeline: IndexingPipeline) -> None:
        self._pipeline = pipeline

    @property
    def name(self) -> str:
        return "index_documents_preview"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Preview indexing impact for local file or directory sources "
                "without mutating storage."
            ),
            parameters=INDEX_DOCUMENTS_PREVIEW_PARAMETERS,
        )

    def execute(self, arguments: dict[str, object]) -> str:
        request = IndexDocumentsPreviewRequest.model_validate(arguments)
        response = index_documents_preview(request, pipeline=self._pipeline)
        return response.model_dump_json()


class IndexDocumentsApplyTool:
    """Adapter for the index_documents_apply MCP handler."""

    def __init__(self, *, pipeline: IndexingPipeline) -> None:
        self._pipeline = pipeline

    @property
    def name(self) -> str:
        return "index_documents_apply"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Apply indexing after explicit human approval "
                "(approval_confirmed must be true)."
            ),
            parameters=INDEX_DOCUMENTS_APPLY_PARAMETERS,
        )

    def execute(self, arguments: dict[str, object]) -> str:
        request = IndexDocumentsApplyRequest.model_validate(arguments)
        response = index_documents_apply(request, pipeline=self._pipeline)
        return response.model_dump_json()


def build_default_tool_registry(
    *,
    retriever: Retriever,
    pipeline: IndexingPipeline,
    settings: McpServerSettings | None = None,
) -> ToolRegistry:
    """Construct a registry with Tier 1 MCP tool adapters."""
    mcp_settings = settings or McpServerSettings()
    registry = ToolRegistry()
    registry.register(
        SearchDocumentsTool(retriever=retriever, settings=mcp_settings),
    )
    registry.register(IndexDocumentsPreviewTool(pipeline=pipeline))
    registry.register(IndexDocumentsApplyTool(pipeline=pipeline))
    return registry
