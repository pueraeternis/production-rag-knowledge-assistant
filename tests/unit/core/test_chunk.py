"""Unit tests for chunk domain models."""

from dataclasses import FrozenInstanceError

import pytest

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.source import LineRange


class TestChunkMetadata:
    @pytest.fixture
    def line_range(self) -> LineRange:
        return LineRange(start_line=1, end_line=10)

    def test_valid_construction(self, line_range: LineRange) -> None:
        metadata = ChunkMetadata(
            document_id=DocumentId("doc-1"),
            section_title="Introduction",
            line_range=line_range,
            chunk_index=0,
        )
        assert metadata.document_id == DocumentId("doc-1")
        assert metadata.section_title == "Introduction"
        assert metadata.line_range == line_range
        assert metadata.chunk_index == 0

    def test_document_id_must_be_non_empty(self, line_range: LineRange) -> None:
        with pytest.raises(ValueError, match="document_id must be non-empty"):
            ChunkMetadata(
                document_id=DocumentId("   "),
                section_title="",
                line_range=line_range,
                chunk_index=0,
            )

    def test_chunk_index_must_be_non_negative(self, line_range: LineRange) -> None:
        with pytest.raises(ValueError, match="chunk_index must be >= 0"):
            ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="",
                line_range=line_range,
                chunk_index=-1,
            )

    def test_immutability(self, line_range: LineRange) -> None:
        metadata = ChunkMetadata(
            document_id=DocumentId("doc-1"),
            section_title="",
            line_range=line_range,
            chunk_index=0,
        )
        with pytest.raises(FrozenInstanceError):
            metadata.chunk_index = 1  # type: ignore[misc]


class TestChunk:
    @pytest.fixture
    def metadata(self) -> ChunkMetadata:
        return ChunkMetadata(
            document_id=DocumentId("doc-1"),
            section_title="Section",
            line_range=LineRange(start_line=1, end_line=5),
            chunk_index=0,
        )

    def test_valid_construction(self, metadata: ChunkMetadata) -> None:
        chunk = Chunk(
            chunk_id=ChunkId("chunk-1"),
            metadata=metadata,
            text="Chunk text content.",
        )
        assert chunk.chunk_id == ChunkId("chunk-1")
        assert chunk.metadata == metadata
        assert chunk.text == "Chunk text content."

    def test_chunk_id_must_be_non_empty(self, metadata: ChunkMetadata) -> None:
        with pytest.raises(ValueError, match="chunk_id must be non-empty"):
            Chunk(chunk_id=ChunkId("   "), metadata=metadata, text="text")

    def test_text_must_be_non_empty(self, metadata: ChunkMetadata) -> None:
        with pytest.raises(ValueError, match="text must be non-empty"):
            Chunk(chunk_id=ChunkId("chunk-1"), metadata=metadata, text="   ")

    def test_immutability(self, metadata: ChunkMetadata) -> None:
        chunk = Chunk(
            chunk_id=ChunkId("chunk-1"),
            metadata=metadata,
            text="text",
        )
        with pytest.raises(FrozenInstanceError):
            chunk.text = "other"  # type: ignore[misc]
