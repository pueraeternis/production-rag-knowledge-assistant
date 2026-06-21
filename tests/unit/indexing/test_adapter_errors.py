"""Unit tests for indexing adapter error handling."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.exceptions import ChunkingError, DocumentLoadError
from knowledge_assistant.indexing.ids import document_id_for_path
from knowledge_assistant.indexing.llamaindex_adapter import load_and_chunk_file


class TestAdapterErrors:
    def test_missing_file_raises_document_load_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.txt"
        settings = IndexingSettings(dense_vector_size=8)

        with pytest.raises(DocumentLoadError, match="failed to read raw source mirror"):
            load_and_chunk_file(
                file_path=str(missing),
                document_id=document_id_for_path(str(missing)),
                settings=settings,
            )

    def test_whitespace_only_file_raises_chunking_error(self, tmp_path: Path) -> None:
        file_path = tmp_path / "blank.txt"
        file_path.write_text("   \n\t\n  ", encoding="utf-8")
        settings = IndexingSettings(
            chunk_size=40,
            chunk_overlap=15,
            dense_vector_size=8,
        )

        with pytest.raises(ChunkingError, match="no chunks"):
            load_and_chunk_file(
                file_path=str(file_path),
                document_id=document_id_for_path(str(file_path)),
                settings=settings,
            )

    def test_splitter_failure_raises_chunking_error(self, tmp_path: Path) -> None:
        file_path = tmp_path / "sample.txt"
        file_path.write_text("valid content", encoding="utf-8")
        settings = IndexingSettings(dense_vector_size=8)
        splitter = MagicMock()
        splitter.split_text.side_effect = RuntimeError("splitter failed")

        with (
            patch(
                "knowledge_assistant.indexing.llamaindex_adapter.SentenceSplitter",
                return_value=splitter,
            ),
            pytest.raises(ChunkingError, match="failed to chunk document"),
        ):
            load_and_chunk_file(
                file_path=str(file_path),
                document_id=document_id_for_path(str(file_path)),
                settings=settings,
            )

    def test_empty_split_result_raises_chunking_error(self, tmp_path: Path) -> None:
        file_path = tmp_path / "sample.txt"
        file_path.write_text("valid content", encoding="utf-8")
        settings = IndexingSettings(dense_vector_size=8)
        splitter = MagicMock()
        splitter.split_text.return_value = []

        with (
            patch(
                "knowledge_assistant.indexing.llamaindex_adapter.SentenceSplitter",
                return_value=splitter,
            ),
            pytest.raises(ChunkingError, match="no chunks"),
        ):
            load_and_chunk_file(
                file_path=str(file_path),
                document_id=document_id_for_path(str(file_path)),
                settings=settings,
            )
