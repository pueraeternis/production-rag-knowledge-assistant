"""Unit tests for deterministic indexing IDs."""

import uuid
from pathlib import Path

import pytest

from knowledge_assistant.core.identifiers import DocumentId
from knowledge_assistant.indexing.ids import (
    INDEXING_ID_NAMESPACE,
    chunk_id_for_chunk,
    document_id_for_path,
    normalize_source_path,
)


class TestNormalizeSourcePath:
    def test_resolves_to_absolute_posix_path(self, tmp_path: Path) -> None:
        relative = tmp_path / "docs" / "guide.md"
        relative.parent.mkdir(parents=True)
        relative.write_text("content", encoding="utf-8")

        normalized = normalize_source_path(str(relative))

        assert normalized == relative.resolve().as_posix()
        assert "\\" not in normalized


class TestDocumentIdForPath:
    def test_same_path_produces_same_document_id(self, tmp_path: Path) -> None:
        file_path = tmp_path / "sample.md"
        file_path.write_text("# Sample", encoding="utf-8")

        first = document_id_for_path(str(file_path))
        second = document_id_for_path(str(file_path))

        assert first == second
        uuid.UUID(first)

    def test_different_paths_produce_different_document_ids(
        self,
        tmp_path: Path,
    ) -> None:
        first_path = tmp_path / "first.md"
        second_path = tmp_path / "second.md"
        first_path.write_text("one", encoding="utf-8")
        second_path.write_text("two", encoding="utf-8")

        assert document_id_for_path(str(first_path)) != document_id_for_path(
            str(second_path),
        )

    def test_document_id_matches_uuid5(self, tmp_path: Path) -> None:
        file_path = tmp_path / "sample.md"
        file_path.write_text("content", encoding="utf-8")
        normalized = normalize_source_path(str(file_path))
        expected = str(uuid.uuid5(INDEXING_ID_NAMESPACE, normalized))

        assert document_id_for_path(str(file_path)) == expected


class TestChunkIdForChunk:
    @pytest.fixture
    def document_id(self, tmp_path: Path) -> DocumentId:
        file_path = tmp_path / "doc.md"
        file_path.write_text("content", encoding="utf-8")
        return document_id_for_path(str(file_path))

    def test_same_inputs_produce_same_chunk_id(self, document_id: DocumentId) -> None:
        first = chunk_id_for_chunk(
            document_id=document_id,
            chunk_index=0,
            text="chunk text",
        )
        second = chunk_id_for_chunk(
            document_id=document_id,
            chunk_index=0,
            text="chunk text",
        )

        assert first == second
        uuid.UUID(first)

    def test_different_text_produces_different_chunk_id(
        self,
        document_id: DocumentId,
    ) -> None:
        first = chunk_id_for_chunk(
            document_id=document_id,
            chunk_index=0,
            text="first chunk",
        )
        second = chunk_id_for_chunk(
            document_id=document_id,
            chunk_index=0,
            text="second chunk",
        )

        assert first != second

    def test_different_index_produces_different_chunk_id(
        self,
        document_id: DocumentId,
    ) -> None:
        first = chunk_id_for_chunk(
            document_id=document_id,
            chunk_index=0,
            text="same text",
        )
        second = chunk_id_for_chunk(
            document_id=document_id,
            chunk_index=1,
            text="same text",
        )

        assert first != second
