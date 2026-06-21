"""Unit tests for Qdrant payload mapping."""

import uuid

import pytest

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.document import DocumentMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.storage.exceptions import PayloadMappingError
from knowledge_assistant.storage.mapping import (
    chunk_upsert_item_to_payload,
    payload_to_chunk,
    payload_to_source_reference,
)
from knowledge_assistant.storage.models import ChunkUpsertItem, SparseVector


def _make_upsert_item(
    *,
    source_uri: str | None = "https://example.com/doc.md",
) -> ChunkUpsertItem:
    chunk = Chunk(
        chunk_id=ChunkId(str(uuid.uuid4())),
        metadata=ChunkMetadata(
            document_id=DocumentId("doc-1"),
            section_title="Introduction",
            line_range=LineRange(start_line=1, end_line=10),
            chunk_index=0,
        ),
        text="Chunk body text.",
    )
    document_metadata = DocumentMetadata(
        title="Architecture Guide",
        path="docs/ARCHITECTURE.md",
        source_uri=source_uri,
    )
    return ChunkUpsertItem(
        chunk=chunk,
        document_metadata=document_metadata,
        dense_vector=tuple(0.0 for _ in range(4)),
        sparse_vector=SparseVector(indices=(0, 1), values=(0.5, 0.3)),
    )


class TestChunkUpsertItemToPayload:
    def test_produces_all_nine_payload_fields(self) -> None:
        item = _make_upsert_item()
        payload = chunk_upsert_item_to_payload(item)

        assert payload == {
            "document_id": "doc-1",
            "document_title": "Architecture Guide",
            "document_path": "docs/ARCHITECTURE.md",
            "source_uri": "https://example.com/doc.md",
            "section_title": "Introduction",
            "start_line": 1,
            "end_line": 10,
            "chunk_index": 0,
            "text": "Chunk body text.",
        }

    def test_source_uri_stored_as_null_when_none(self) -> None:
        item = _make_upsert_item(source_uri=None)
        payload = chunk_upsert_item_to_payload(item)
        assert payload["source_uri"] is None


class TestPayloadToChunk:
    def test_reconstructs_chunk_from_payload(self) -> None:
        item = _make_upsert_item()
        payload = chunk_upsert_item_to_payload(item)
        chunk = payload_to_chunk(payload, chunk_id=item.chunk.chunk_id)

        assert chunk == item.chunk

    @pytest.mark.parametrize("missing_key", ["document_id", "text", "start_line"])
    def test_raises_on_missing_required_field(self, missing_key: str) -> None:
        item = _make_upsert_item()
        payload = dict(chunk_upsert_item_to_payload(item))
        del payload[missing_key]

        with pytest.raises(PayloadMappingError, match="missing required payload field"):
            payload_to_chunk(payload, chunk_id=item.chunk.chunk_id)

    def test_raises_on_invalid_field_type(self) -> None:
        item = _make_upsert_item()
        payload = dict(chunk_upsert_item_to_payload(item))
        payload["chunk_index"] = "zero"

        with pytest.raises(PayloadMappingError, match="chunk_index must be int"):
            payload_to_chunk(payload, chunk_id=item.chunk.chunk_id)


class TestPayloadToSourceReference:
    def test_reconstructs_source_reference_from_payload(self) -> None:
        item = _make_upsert_item()
        payload = chunk_upsert_item_to_payload(item)
        reference = payload_to_source_reference(payload)

        assert reference == SourceReference(
            document_title="Architecture Guide",
            document_path="docs/ARCHITECTURE.md",
            section_title="Introduction",
            line_range=LineRange(start_line=1, end_line=10),
        )

    def test_round_trip_citation_fields_match_document_metadata(self) -> None:
        item = _make_upsert_item()
        payload = chunk_upsert_item_to_payload(item)
        reference = payload_to_source_reference(payload)

        assert reference.document_title == item.document_metadata.title
        assert reference.document_path == item.document_metadata.path
        assert reference.section_title == item.chunk.metadata.section_title
        assert reference.line_range == item.chunk.metadata.line_range

    def test_chunk_upsert_item_to_source_reference_round_trip(self) -> None:
        item = _make_upsert_item()
        payload = chunk_upsert_item_to_payload(item)
        reference = payload_to_source_reference(payload)

        assert reference.document_title == "Architecture Guide"
        assert reference.document_path == "docs/ARCHITECTURE.md"
        assert reference.section_title == "Introduction"
        assert reference.line_range == LineRange(start_line=1, end_line=10)
