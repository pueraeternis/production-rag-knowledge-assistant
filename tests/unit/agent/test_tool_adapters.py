"""Unit tests for MCP tool adapters."""

import json
from unittest.mock import MagicMock

from knowledge_assistant.agent.tools import ToolRegistry
from knowledge_assistant.agent.wiring import (
    IndexDocumentsApplyTool,
    IndexDocumentsPreviewTool,
    SearchDocumentsTool,
    build_default_tool_registry,
)
from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.indexing import (
    IndexingPreview,
    IndexingSource,
    IndexingSourceKind,
)
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.indexing.pipeline import IndexingResult
from knowledge_assistant.llm.messages import ToolCall
from knowledge_assistant.mcp_server.config import McpServerSettings
from knowledge_assistant.mcp_server.exceptions import APPROVAL_REQUIRED


def _search_result() -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=ChunkId("chunk-1"),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Overview",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text="policy text",
        ),
        score=0.9,
        source=SourceReference(
            document_title="Guide",
            document_path="docs/guide.md",
            section_title="Overview",
            line_range=LineRange(start_line=1, end_line=5),
        ),
    )


class TestSearchDocumentsTool:
    def test_execute_returns_mcp_json(self) -> None:
        retriever = MagicMock()
        retriever.retrieve.return_value = RetrievalResult(
            query=SearchQuery(text="policy", top_k=3),
            results=(_search_result(),),
        )
        tool = SearchDocumentsTool(
            retriever=retriever,
            settings=McpServerSettings(default_top_k=3),
        )

        payload = json.loads(
            tool.execute({"query": "policy", "top_k": 3}),
        )

        assert payload["query"] == "policy"
        assert payload["hits"][0]["source"]["document_path"] == "docs/guide.md"


class TestIndexingTools:
    def test_preview_tool_returns_preview_json(self) -> None:
        pipeline = MagicMock()
        source = IndexingSource(
            kind=IndexingSourceKind.FILE,
            location="docs/a.md",
            recursive=False,
        )
        pipeline.preview_indexing.return_value = IndexingPreview(
            sources=(source,),
            document_count=1,
            chunk_count=2,
            replaces_existing=False,
        )
        tool = IndexDocumentsPreviewTool(pipeline=pipeline)

        payload = json.loads(
            tool.execute(
                {
                    "sources": [
                        {
                            "kind": "file",
                            "location": "docs/a.md",
                        },
                    ],
                },
            ),
        )

        assert payload["chunk_count"] == 2

    def test_apply_without_approval_returns_error_via_registry(self) -> None:
        pipeline = MagicMock()
        tool = IndexDocumentsApplyTool(pipeline=pipeline)

        registry = ToolRegistry()
        registry.register(tool)
        message = registry.dispatch(
            ToolCall(
                id="call-apply",
                name="index_documents_apply",
                arguments=json.dumps(
                    {
                        "sources": [
                            {"kind": "file", "location": "docs/a.md"},
                        ],
                        "approval_confirmed": False,
                    },
                ),
            ),
        )

        payload = json.loads(message.content or "{}")
        assert payload["error"] == APPROVAL_REQUIRED
        pipeline.index_documents.assert_not_called()

    def test_apply_with_approval_calls_pipeline(self) -> None:
        pipeline = MagicMock()
        source = IndexingSource(
            kind=IndexingSourceKind.FILE,
            location="docs/a.md",
            recursive=False,
        )
        pipeline.index_documents.return_value = IndexingResult(
            sources=(source,),
            document_count=1,
            chunk_count=2,
            upserted_count=2,
            rebuilt=False,
        )
        tool = IndexDocumentsApplyTool(pipeline=pipeline)

        payload = json.loads(
            tool.execute(
                {
                    "sources": [{"kind": "file", "location": "docs/a.md"}],
                    "approval_confirmed": True,
                },
            ),
        )

        assert payload["upserted_count"] == 2
        pipeline.index_documents.assert_called_once()


class TestBuildDefaultToolRegistry:
    def test_registers_three_tier_one_tools(self) -> None:
        registry = build_default_tool_registry(
            retriever=MagicMock(),
            pipeline=MagicMock(),
        )
        names = {definition.name for definition in registry.definitions()}
        assert names == {
            "index_documents_apply",
            "index_documents_preview",
            "search_documents",
        }
