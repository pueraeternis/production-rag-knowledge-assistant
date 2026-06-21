"""Fakes for MCP handler integration tests."""

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


class FakeRetriever:
    """Configurable retriever fake that records the last SearchQuery."""

    def __init__(self, *, return_value: RetrievalResult) -> None:
        self._return_value = return_value
        self.last_query: SearchQuery | None = None

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        self.last_query = query
        return self._return_value


class FakeIndexingPipeline:
    """Configurable indexing pipeline fake for handler integration tests."""

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


def make_search_result() -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=ChunkId("chunk-1"),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Overview",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text="integration chunk text",
        ),
        score=0.75,
        source=SourceReference(
            document_title="Guide",
            document_path="docs/guide.md",
            section_title="Overview",
            line_range=LineRange(start_line=1, end_line=5),
        ),
    )


def make_preview() -> IndexingPreview:
    source = IndexingSource(
        kind=IndexingSourceKind.DIRECTORY,
        location="docs",
        recursive=True,
    )
    return IndexingPreview(
        sources=(source,),
        document_count=2,
        chunk_count=6,
        replaces_existing=True,
    )


def make_index_result() -> IndexingResult:
    source = IndexingSource(
        kind=IndexingSourceKind.DIRECTORY,
        location="docs",
        recursive=True,
    )
    return IndexingResult(
        sources=(source,),
        document_count=2,
        chunk_count=6,
        upserted_count=6,
        rebuilt=False,
    )
