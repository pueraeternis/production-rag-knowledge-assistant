"""Unit tests for MCP formatting helpers."""

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.indexing import (
    IndexingPreview,
    IndexingSource,
    IndexingSourceKind,
)
from knowledge_assistant.core.retrieval import SearchResult
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.indexing.pipeline import IndexingResult
from knowledge_assistant.mcp_server.formatting import (
    format_index_documents_apply_response,
    format_index_documents_preview_response,
    format_search_documents_response,
    format_search_hit,
    format_source_reference,
    indexing_source_from_schema,
    indexing_source_to_schema,
)
from knowledge_assistant.mcp_server.schemas import IndexingSourceSchema


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
            text="chunk text",
        ),
        score=0.88,
        source=SourceReference(
            document_title="Guide",
            document_path="docs/guide.md",
            section_title="Overview",
            line_range=LineRange(start_line=1, end_line=5),
        ),
    )


class TestFormatting:
    def test_format_source_reference_maps_all_citation_fields(self) -> None:
        source = SourceReference(
            document_title="Guide",
            document_path="docs/guide.md",
            section_title="Overview",
            line_range=LineRange(start_line=2, end_line=8),
        )

        schema = format_source_reference(source)

        assert schema.document_title == "Guide"
        assert schema.document_path == "docs/guide.md"
        assert schema.section_title == "Overview"
        assert schema.line_range.start_line == 2
        assert schema.line_range.end_line == 8

    def test_format_search_hit_includes_chunk_id_text_score_and_source(self) -> None:
        hit = format_search_hit(_make_search_result())

        assert hit.chunk_id == "chunk-1"
        assert hit.text == "chunk text"
        assert hit.score == 0.88
        assert hit.source.document_path == "docs/guide.md"

    def test_format_search_documents_response(self) -> None:
        response = format_search_documents_response(
            query="python retrieval",
            top_k=3,
            results=(_make_search_result(),),
        )

        assert response.query == "python retrieval"
        assert response.top_k == 3
        assert len(response.hits) == 1

    def test_indexing_source_schema_round_trip(self) -> None:
        schema = IndexingSourceSchema(
            kind="directory",
            location="docs",
            recursive=True,
        )

        source = indexing_source_from_schema(schema)
        round_trip = indexing_source_to_schema(source)

        assert source.kind is IndexingSourceKind.DIRECTORY
        assert source.location == "docs"
        assert source.recursive is True
        assert round_trip == schema

    def test_format_index_documents_preview_response(self) -> None:
        source = IndexingSource(
            kind=IndexingSourceKind.FILE,
            location="docs/a.md",
            recursive=False,
        )
        preview = IndexingPreview(
            sources=(source,),
            document_count=1,
            chunk_count=4,
            replaces_existing=True,
        )

        response = format_index_documents_preview_response(preview)

        assert response.document_count == 1
        assert response.chunk_count == 4
        assert response.replaces_existing is True
        assert response.sources[0].location == "docs/a.md"

    def test_format_index_documents_apply_response(self) -> None:
        source = IndexingSource(
            kind=IndexingSourceKind.FILE,
            location="docs/a.md",
            recursive=False,
        )
        result = IndexingResult(
            sources=(source,),
            document_count=1,
            chunk_count=4,
            upserted_count=4,
            rebuilt=False,
        )

        response = format_index_documents_apply_response(result)

        assert response.upserted_count == 4
        assert response.rebuilt is False
