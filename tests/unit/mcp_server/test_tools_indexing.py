"""Unit tests for indexing MCP handlers."""

from typing import cast

import pytest

from knowledge_assistant.core.indexing import (
    IndexingPreview,
    IndexingSource,
    IndexingSourceKind,
)
from knowledge_assistant.indexing.pipeline import IndexingPipeline, IndexingResult
from knowledge_assistant.mcp_server.exceptions import ApprovalRequiredError
from knowledge_assistant.mcp_server.schemas import (
    IndexDocumentsApplyRequest,
    IndexDocumentsPreviewRequest,
    IndexingSourceSchema,
)
from knowledge_assistant.mcp_server.tools import (
    index_documents_apply,
    index_documents_preview,
)


class FakeIndexingPipeline:
    """Records indexing calls for handler tests."""

    def __init__(
        self,
        *,
        preview_return: IndexingPreview | None = None,
        index_return: IndexingResult | None = None,
    ) -> None:
        self.preview_return = preview_return
        self.index_return = index_return
        self.preview_call_count = 0
        self.index_call_count = 0
        self.last_sources: tuple[IndexingSource, ...] | None = None
        self.last_rebuild: bool | None = None

    def preview_indexing(
        self,
        sources: tuple[IndexingSource, ...],
    ) -> IndexingPreview:
        self.preview_call_count += 1
        self.last_sources = sources
        assert self.preview_return is not None
        return self.preview_return

    def index_documents(
        self,
        sources: tuple[IndexingSource, ...],
        *,
        rebuild: bool = False,
    ) -> IndexingResult:
        self.index_call_count += 1
        self.last_sources = sources
        self.last_rebuild = rebuild
        assert self.index_return is not None
        return self.index_return


def _preview() -> IndexingPreview:
    source = IndexingSource(
        kind=IndexingSourceKind.FILE,
        location="docs/a.md",
        recursive=False,
    )
    return IndexingPreview(
        sources=(source,),
        document_count=1,
        chunk_count=3,
        replaces_existing=False,
    )


def _index_result(*, rebuilt: bool = False) -> IndexingResult:
    source = IndexingSource(
        kind=IndexingSourceKind.FILE,
        location="docs/a.md",
        recursive=False,
    )
    return IndexingResult(
        sources=(source,),
        document_count=1,
        chunk_count=3,
        upserted_count=3,
        rebuilt=rebuilt,
    )


class TestIndexDocumentsPreview:
    def test_delegates_to_pipeline_without_mutation(self) -> None:
        pipeline = FakeIndexingPipeline(preview_return=_preview())
        request = IndexDocumentsPreviewRequest(
            sources=(IndexingSourceSchema(kind="file", location="docs/a.md"),),
        )

        response = index_documents_preview(
            request,
            pipeline=cast(IndexingPipeline, pipeline),
        )

        assert pipeline.preview_call_count == 1
        assert pipeline.index_call_count == 0
        assert pipeline.last_sources is not None
        assert pipeline.last_sources[0].kind is IndexingSourceKind.FILE
        assert response.document_count == 1
        assert response.chunk_count == 3


class TestIndexDocumentsApply:
    def test_requires_approval_before_indexing(self) -> None:
        pipeline = FakeIndexingPipeline(index_return=_index_result())
        request = IndexDocumentsApplyRequest(
            sources=(IndexingSourceSchema(kind="file", location="docs/a.md"),),
            approval_confirmed=False,
        )

        with pytest.raises(ApprovalRequiredError):
            index_documents_apply(
                request,
                pipeline=cast(IndexingPipeline, pipeline),
            )

        assert pipeline.index_call_count == 0

    def test_calls_index_documents_when_approved(self) -> None:
        pipeline = FakeIndexingPipeline(index_return=_index_result(rebuilt=True))
        request = IndexDocumentsApplyRequest(
            sources=(IndexingSourceSchema(kind="file", location="docs/a.md"),),
            approval_confirmed=True,
            rebuild=True,
        )

        response = index_documents_apply(
            request,
            pipeline=cast(IndexingPipeline, pipeline),
        )

        assert pipeline.index_call_count == 1
        assert pipeline.last_rebuild is True
        assert response.upserted_count == 3
        assert response.rebuilt is True
