"""Map core domain types to MCP Pydantic response models."""

from typing import Literal

from knowledge_assistant.core.indexing import (
    IndexingPreview,
    IndexingSource,
    IndexingSourceKind,
)
from knowledge_assistant.core.retrieval import SearchResult
from knowledge_assistant.core.source import SourceReference
from knowledge_assistant.indexing.pipeline import IndexingResult
from knowledge_assistant.mcp_server.schemas import (
    IndexDocumentsApplyResponse,
    IndexDocumentsPreviewResponse,
    IndexingSourceSchema,
    LineRangeSchema,
    SearchDocumentsResponse,
    SearchHitSchema,
    SourceReferenceSchema,
)


def format_source_reference(source: SourceReference) -> SourceReferenceSchema:
    """Map a core SourceReference to its MCP citation schema."""
    return SourceReferenceSchema(
        document_title=source.document_title,
        document_path=source.document_path,
        section_title=source.section_title,
        line_range=LineRangeSchema(
            start_line=source.line_range.start_line,
            end_line=source.line_range.end_line,
        ),
    )


def format_search_hit(result: SearchResult) -> SearchHitSchema:
    """Map one SearchResult to a SearchHitSchema."""
    return SearchHitSchema(
        chunk_id=str(result.chunk.chunk_id),
        text=result.chunk.text,
        score=result.score,
        source=format_source_reference(result.source),
    )


def format_search_documents_response(
    *,
    query: str,
    top_k: int,
    results: tuple[SearchResult, ...],
) -> SearchDocumentsResponse:
    """Map retrieval hits to a search_documents response."""
    return SearchDocumentsResponse(
        query=query,
        top_k=top_k,
        hits=tuple(format_search_hit(result) for result in results),
    )


def indexing_source_to_schema(source: IndexingSource) -> IndexingSourceSchema:
    """Map a core IndexingSource to its MCP schema."""
    kind: Literal["file", "directory"]
    if source.kind is IndexingSourceKind.FILE:
        kind = "file"
    elif source.kind is IndexingSourceKind.DIRECTORY:
        kind = "directory"
    else:
        msg = f"unsupported indexing source kind for MCP: {source.kind.value}"
        raise ValueError(msg)
    return IndexingSourceSchema(
        kind=kind,
        location=source.location,
        recursive=source.recursive,
    )


def indexing_source_from_schema(schema: IndexingSourceSchema) -> IndexingSource:
    """Map an MCP indexing source schema to the core domain type."""
    kind = (
        IndexingSourceKind.FILE
        if schema.kind == "file"
        else IndexingSourceKind.DIRECTORY
    )
    return IndexingSource(
        kind=kind,
        location=schema.location,
        recursive=schema.recursive,
    )


def indexing_sources_from_schemas(
    schemas: tuple[IndexingSourceSchema, ...],
) -> tuple[IndexingSource, ...]:
    """Map MCP indexing source schemas to core domain types."""
    return tuple(indexing_source_from_schema(schema) for schema in schemas)


def format_indexing_sources(
    sources: tuple[IndexingSource, ...],
) -> tuple[IndexingSourceSchema, ...]:
    """Map core indexing sources to MCP schemas."""
    return tuple(indexing_source_to_schema(source) for source in sources)


def format_index_documents_preview_response(
    preview: IndexingPreview,
) -> IndexDocumentsPreviewResponse:
    """Map an IndexingPreview to its MCP response."""
    return IndexDocumentsPreviewResponse(
        sources=format_indexing_sources(preview.sources),
        document_count=preview.document_count,
        chunk_count=preview.chunk_count,
        replaces_existing=preview.replaces_existing,
    )


def format_index_documents_apply_response(
    result: IndexingResult,
) -> IndexDocumentsApplyResponse:
    """Map an IndexingResult to its MCP response."""
    return IndexDocumentsApplyResponse(
        sources=format_indexing_sources(result.sources),
        document_count=result.document_count,
        chunk_count=result.chunk_count,
        upserted_count=result.upserted_count,
        rebuilt=result.rebuilt,
    )
