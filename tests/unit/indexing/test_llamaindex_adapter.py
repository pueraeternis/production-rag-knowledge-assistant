"""Unit tests for the LlamaIndex adapter and line attribution."""

from pathlib import Path

import pytest

from knowledge_assistant.core.source import LineRange
from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.ids import document_id_for_path, normalize_source_path
from knowledge_assistant.indexing.llamaindex_adapter import load_and_chunk_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestLoadAndChunkFile:
    @pytest.fixture
    def small_chunk_settings(self) -> IndexingSettings:
        return IndexingSettings(chunk_size=40, chunk_overlap=0, dense_vector_size=8)

    def test_maps_plain_text_metadata(
        self,
        small_chunk_settings: IndexingSettings,
    ) -> None:
        file_path = FIXTURES_DIR / "sample.txt"
        document_id = document_id_for_path(str(file_path))

        metadata, chunks = load_and_chunk_file(
            file_path=str(file_path),
            document_id=document_id,
            settings=small_chunk_settings,
        )

        assert metadata.title == "sample"
        assert metadata.path == normalize_source_path(str(file_path))
        assert metadata.source_uri is None
        assert chunks
        assert all(chunk.metadata.document_id == document_id for chunk in chunks)
        assert all(chunk.metadata.section_title == "" for chunk in chunks)

    def test_markdown_title_from_first_heading(
        self,
        small_chunk_settings: IndexingSettings,
    ) -> None:
        file_path = FIXTURES_DIR / "sample.md"
        document_id = document_id_for_path(str(file_path))

        metadata, _ = load_and_chunk_file(
            file_path=str(file_path),
            document_id=document_id,
            settings=small_chunk_settings,
        )

        assert metadata.title == "Fixture Title"

    def test_markdown_section_titles(
        self,
        small_chunk_settings: IndexingSettings,
    ) -> None:
        file_path = FIXTURES_DIR / "sample.md"
        document_id = document_id_for_path(str(file_path))

        _, chunks = load_and_chunk_file(
            file_path=str(file_path),
            document_id=document_id,
            settings=small_chunk_settings,
        )

        section_titles = {chunk.metadata.section_title for chunk in chunks}
        assert "Section One" in section_titles
        assert "Section Two" in section_titles

    def test_line_ranges_are_valid(
        self,
        small_chunk_settings: IndexingSettings,
    ) -> None:
        file_path = FIXTURES_DIR / "sample.txt"
        document_id = document_id_for_path(str(file_path))

        _, chunks = load_and_chunk_file(
            file_path=str(file_path),
            document_id=document_id,
            settings=small_chunk_settings,
        )

        for chunk in chunks:
            line_range = chunk.metadata.line_range
            assert line_range.start_line >= 1
            assert line_range.end_line >= line_range.start_line

    def test_plain_text_single_chunk_line_range(self) -> None:
        file_path = FIXTURES_DIR / "sample.txt"
        document_id = document_id_for_path(str(file_path))
        settings = IndexingSettings(
            chunk_size=1024,
            chunk_overlap=0,
            dense_vector_size=8,
        )

        _, chunks = load_and_chunk_file(
            file_path=str(file_path),
            document_id=document_id,
            settings=settings,
        )

        assert len(chunks) == 1
        assert chunks[0].metadata.line_range == LineRange(start_line=1, end_line=3)

    def test_markdown_chunk_line_ranges_with_small_chunks(self) -> None:
        file_path = FIXTURES_DIR / "sample.md"
        document_id = document_id_for_path(str(file_path))
        settings = IndexingSettings(chunk_size=30, chunk_overlap=0, dense_vector_size=8)

        _, chunks = load_and_chunk_file(
            file_path=str(file_path),
            document_id=document_id,
            settings=settings,
        )

        line_ranges = [chunk.metadata.line_range for chunk in chunks]
        assert line_ranges == [
            LineRange(start_line=1, end_line=3),
            LineRange(start_line=3, end_line=5),
            LineRange(start_line=6, end_line=8),
            LineRange(start_line=8, end_line=10),
            LineRange(start_line=10, end_line=11),
        ]

    def test_chunk_ids_are_assigned(
        self,
        small_chunk_settings: IndexingSettings,
    ) -> None:
        file_path = FIXTURES_DIR / "sample.txt"
        document_id = document_id_for_path(str(file_path))

        _, chunks = load_and_chunk_file(
            file_path=str(file_path),
            document_id=document_id,
            settings=small_chunk_settings,
        )

        chunk_ids = [chunk.chunk_id for chunk in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_overlap_chunks_have_valid_deterministic_line_ranges(self) -> None:
        file_path = FIXTURES_DIR / "overlap.txt"
        document_id = document_id_for_path(str(file_path))
        settings = IndexingSettings(
            chunk_size=40,
            chunk_overlap=15,
            dense_vector_size=8,
        )

        _, first_run = load_and_chunk_file(
            file_path=str(file_path),
            document_id=document_id,
            settings=settings,
        )
        _, second_run = load_and_chunk_file(
            file_path=str(file_path),
            document_id=document_id,
            settings=settings,
        )

        assert len(first_run) > 1
        first_ranges = [chunk.metadata.line_range for chunk in first_run]
        second_ranges = [chunk.metadata.line_range for chunk in second_run]
        assert first_ranges == second_ranges
        for line_range in first_ranges:
            assert line_range.start_line >= 1
            assert line_range.end_line >= line_range.start_line

    def test_overlap_chunks_cover_progressive_source_lines(self) -> None:
        file_path = FIXTURES_DIR / "overlap.txt"
        document_id = document_id_for_path(str(file_path))
        settings = IndexingSettings(
            chunk_size=40,
            chunk_overlap=15,
            dense_vector_size=8,
        )

        _, chunks = load_and_chunk_file(
            file_path=str(file_path),
            document_id=document_id,
            settings=settings,
        )

        max_end_line = max(chunk.metadata.line_range.end_line for chunk in chunks)
        assert max_end_line >= 3
        assert any(
            chunk.metadata.line_range.end_line > chunk.metadata.line_range.start_line
            for chunk in chunks
        )
