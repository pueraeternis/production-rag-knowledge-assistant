"""Pure payload translation between domain models and Qdrant payloads."""

from collections.abc import Mapping

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.storage.exceptions import PayloadMappingError
from knowledge_assistant.storage.models import ChunkUpsertItem

_PAYLOAD_KEYS = (
    "document_id",
    "document_title",
    "document_path",
    "source_uri",
    "section_title",
    "start_line",
    "end_line",
    "chunk_index",
    "text",
)


def chunk_upsert_item_to_payload(item: ChunkUpsertItem) -> dict[str, object]:
    """Map a storage upsert item to a flat Qdrant payload dict."""
    chunk = item.chunk
    document_metadata = item.document_metadata
    return {
        "document_id": str(chunk.metadata.document_id),
        "document_title": document_metadata.title,
        "document_path": document_metadata.path,
        "source_uri": document_metadata.source_uri,
        "section_title": chunk.metadata.section_title,
        "start_line": chunk.metadata.line_range.start_line,
        "end_line": chunk.metadata.line_range.end_line,
        "chunk_index": chunk.metadata.chunk_index,
        "text": chunk.text,
    }


def _require_str(payload: Mapping[str, object], key: str) -> str:
    if key not in payload:
        msg = f"missing required payload field: {key}"
        raise PayloadMappingError(msg)
    value = payload[key]
    if not isinstance(value, str):
        msg = f"payload field {key} must be str, got {type(value).__name__}"
        raise PayloadMappingError(msg)
    return value


def _require_int(payload: Mapping[str, object], key: str) -> int:
    if key not in payload:
        msg = f"missing required payload field: {key}"
        raise PayloadMappingError(msg)
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"payload field {key} must be int, got {type(value).__name__}"
        raise PayloadMappingError(msg)
    return value


def payload_to_chunk(payload: Mapping[str, object], *, chunk_id: ChunkId) -> Chunk:
    """Reconstruct a domain Chunk from a Qdrant payload and point identifier."""
    for key in _PAYLOAD_KEYS:
        if key not in payload:
            msg = f"missing required payload field: {key}"
            raise PayloadMappingError(msg)

    line_range = LineRange(
        start_line=_require_int(payload, "start_line"),
        end_line=_require_int(payload, "end_line"),
    )
    metadata = ChunkMetadata(
        document_id=DocumentId(_require_str(payload, "document_id")),
        section_title=_require_str(payload, "section_title"),
        line_range=line_range,
        chunk_index=_require_int(payload, "chunk_index"),
    )
    return Chunk(
        chunk_id=chunk_id,
        metadata=metadata,
        text=_require_str(payload, "text"),
    )


def payload_to_source_reference(payload: Mapping[str, object]) -> SourceReference:
    """Reconstruct a SourceReference from Qdrant citation payload fields."""
    line_range = LineRange(
        start_line=_require_int(payload, "start_line"),
        end_line=_require_int(payload, "end_line"),
    )
    return SourceReference(
        document_title=_require_str(payload, "document_title"),
        document_path=_require_str(payload, "document_path"),
        section_title=_require_str(payload, "section_title"),
        line_range=line_range,
    )
