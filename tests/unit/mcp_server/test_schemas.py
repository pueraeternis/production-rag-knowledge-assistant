"""Unit tests for MCP Pydantic schemas."""

import pytest
from pydantic import ValidationError

from knowledge_assistant.mcp_server.schemas import (
    IndexDocumentsApplyRequest,
    IndexDocumentsPreviewRequest,
    IndexingSourceSchema,
    SearchDocumentsRequest,
)


class TestSearchDocumentsRequest:
    def test_valid_construction(self) -> None:
        request = SearchDocumentsRequest(query="hybrid retrieval", top_k=5)
        assert request.query == "hybrid retrieval"
        assert request.top_k == 5

    def test_top_k_optional(self) -> None:
        request = SearchDocumentsRequest(query="query")
        assert request.top_k is None

    def test_query_must_be_non_empty_after_strip(self) -> None:
        with pytest.raises(ValidationError):
            SearchDocumentsRequest(query="   ")

    @pytest.mark.parametrize("top_k", [0, -1])
    def test_top_k_must_be_at_least_one(self, top_k: int) -> None:
        with pytest.raises(ValidationError):
            SearchDocumentsRequest(query="query", top_k=top_k)


class TestIndexingSourceSchema:
    def test_valid_file_source(self) -> None:
        source = IndexingSourceSchema(kind="file", location="docs/guide.md")
        assert source.kind == "file"
        assert source.recursive is False

    def test_location_must_be_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            IndexingSourceSchema(kind="directory", location="   ")


class TestIndexDocumentsPreviewRequest:
    def test_sources_must_be_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            IndexDocumentsPreviewRequest(sources=())


class TestIndexDocumentsApplyRequest:
    def test_requires_approval_field(self) -> None:
        request = IndexDocumentsApplyRequest(
            sources=(IndexingSourceSchema(kind="file", location="docs/a.md"),),
            approval_confirmed=False,
        )
        assert request.approval_confirmed is False

    def test_rebuild_defaults_to_false(self) -> None:
        request = IndexDocumentsApplyRequest(
            sources=(IndexingSourceSchema(kind="file", location="docs/a.md"),),
            approval_confirmed=True,
        )
        assert request.rebuild is False
