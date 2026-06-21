"""Unit tests for LlamaIndex reader integration in the adapter."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.exceptions import DocumentLoadError
from knowledge_assistant.indexing.ids import document_id_for_path
from knowledge_assistant.indexing.llamaindex_adapter import load_and_chunk_file


class TestLlamaIndexReader:
    def test_reader_is_called_for_valid_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "sample.txt"
        file_path.write_text("hello world", encoding="utf-8")
        settings = IndexingSettings(
            chunk_size=1024,
            chunk_overlap=0,
            dense_vector_size=8,
        )

        with patch(
            "knowledge_assistant.indexing.llamaindex_adapter.SimpleDirectoryReader",
        ) as reader_cls:
            reader_cls.return_value.load_data.return_value = [
                MagicMock(text="hello world"),
            ]
            load_and_chunk_file(
                file_path=str(file_path),
                document_id=document_id_for_path(str(file_path)),
                settings=settings,
            )

        reader_cls.assert_called_once_with(input_files=[str(file_path)])
        reader_cls.return_value.load_data.assert_called_once_with()

    def test_reader_returning_no_documents_raises_document_load_error(
        self,
        tmp_path: Path,
    ) -> None:
        file_path = tmp_path / "sample.txt"
        file_path.write_text("hello world", encoding="utf-8")
        settings = IndexingSettings(dense_vector_size=8)

        with patch(
            "knowledge_assistant.indexing.llamaindex_adapter.SimpleDirectoryReader",
        ) as reader_cls:
            reader_cls.return_value.load_data.return_value = []
            with pytest.raises(DocumentLoadError, match="no documents"):
                load_and_chunk_file(
                    file_path=str(file_path),
                    document_id=document_id_for_path(str(file_path)),
                    settings=settings,
                )

    def test_reader_returning_multiple_documents_raises_document_load_error(
        self,
        tmp_path: Path,
    ) -> None:
        file_path = tmp_path / "sample.txt"
        file_path.write_text("hello world", encoding="utf-8")
        settings = IndexingSettings(dense_vector_size=8)

        with patch(
            "knowledge_assistant.indexing.llamaindex_adapter.SimpleDirectoryReader",
        ) as reader_cls:
            reader_cls.return_value.load_data.return_value = [
                MagicMock(text="one"),
                MagicMock(text="two"),
            ]
            with pytest.raises(DocumentLoadError, match="multiple documents"):
                load_and_chunk_file(
                    file_path=str(file_path),
                    document_id=document_id_for_path(str(file_path)),
                    settings=settings,
                )

    def test_splitter_receives_llamaindex_loaded_text_not_raw_mirror(
        self,
        tmp_path: Path,
    ) -> None:
        file_path = tmp_path / "sample.txt"
        file_path.write_text("raw text", encoding="utf-8")
        settings = IndexingSettings(
            chunk_size=1024,
            chunk_overlap=0,
            dense_vector_size=8,
        )
        splitter = MagicMock()
        splitter.split_text.return_value = ["loaded text"]

        with (
            patch(
                "knowledge_assistant.indexing.llamaindex_adapter.SimpleDirectoryReader",
            ) as reader_cls,
            patch(
                "knowledge_assistant.indexing.llamaindex_adapter.SentenceSplitter",
                return_value=splitter,
            ),
        ):
            reader_cls.return_value.load_data.return_value = [
                MagicMock(text="loaded text"),
            ]
            _, chunks = load_and_chunk_file(
                file_path=str(file_path),
                document_id=document_id_for_path(str(file_path)),
                settings=settings,
            )

        splitter.split_text.assert_called_once_with("loaded text")
        assert len(chunks) == 1
        assert chunks[0].text == "loaded text"
