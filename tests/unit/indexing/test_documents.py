"""Unit tests for local file discovery."""

from pathlib import Path

import pytest

from knowledge_assistant.core.indexing import IndexingSource, IndexingSourceKind
from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.documents import discover_files
from knowledge_assistant.indexing.exceptions import (
    SourceNotFoundError,
    UnsupportedFileTypeError,
    UnsupportedSourceKindError,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestDiscoverFiles:
    @pytest.fixture
    def settings(self) -> IndexingSettings:
        return IndexingSettings()

    def test_single_file_source(self, settings: IndexingSettings) -> None:
        file_path = FIXTURES_DIR / "sample.txt"
        source = IndexingSource(
            kind=IndexingSourceKind.FILE,
            location=str(file_path),
            recursive=False,
        )

        discovered = discover_files(source, settings=settings)

        assert discovered == (file_path.resolve().as_posix(),)

    def test_recursive_directory_discovery(self, settings: IndexingSettings) -> None:
        source = IndexingSource(
            kind=IndexingSourceKind.DIRECTORY,
            location=str(FIXTURES_DIR),
            recursive=True,
        )

        discovered = discover_files(source, settings=settings)

        assert str(FIXTURES_DIR / "sample.txt") in discovered
        assert str(FIXTURES_DIR / "sample.md") in discovered
        assert str(FIXTURES_DIR / "top.txt") in discovered
        assert str(FIXTURES_DIR / "nested" / "deep" / "nested.md") in discovered
        assert str(FIXTURES_DIR / "ignored.pdf") not in discovered
        assert discovered == tuple(sorted(discovered))

    def test_non_recursive_directory_excludes_nested_files(
        self,
        settings: IndexingSettings,
    ) -> None:
        source = IndexingSource(
            kind=IndexingSourceKind.DIRECTORY,
            location=str(FIXTURES_DIR),
            recursive=False,
        )

        discovered = discover_files(source, settings=settings)

        assert str(FIXTURES_DIR / "top.txt") in discovered
        assert str(FIXTURES_DIR / "nested" / "deep" / "nested.md") not in discovered

    @pytest.mark.parametrize(
        "kind",
        [IndexingSourceKind.DOCUMENT_URL, IndexingSourceKind.DIRECTORY_URL],
    )
    def test_unsupported_source_kind_raises(
        self,
        kind: IndexingSourceKind,
        settings: IndexingSettings,
    ) -> None:
        source = IndexingSource(
            kind=kind,
            location="https://example.com/docs",
            recursive=False,
        )

        with pytest.raises(UnsupportedSourceKindError):
            discover_files(source, settings=settings)

    def test_unsupported_extension_on_file_source_raises(
        self,
        settings: IndexingSettings,
    ) -> None:
        source = IndexingSource(
            kind=IndexingSourceKind.FILE,
            location=str(FIXTURES_DIR / "ignored.pdf"),
            recursive=False,
        )

        with pytest.raises(UnsupportedFileTypeError):
            discover_files(source, settings=settings)

    def test_directory_walk_skips_unsupported_extensions(
        self,
        settings: IndexingSettings,
    ) -> None:
        source = IndexingSource(
            kind=IndexingSourceKind.DIRECTORY,
            location=str(FIXTURES_DIR),
            recursive=True,
        )

        discovered = discover_files(source, settings=settings)

        assert all(not path.endswith(".pdf") for path in discovered)

    def test_missing_source_raises(self, settings: IndexingSettings) -> None:
        source = IndexingSource(
            kind=IndexingSourceKind.FILE,
            location=str(FIXTURES_DIR / "missing.txt"),
            recursive=False,
        )

        with pytest.raises(SourceNotFoundError):
            discover_files(source, settings=settings)
