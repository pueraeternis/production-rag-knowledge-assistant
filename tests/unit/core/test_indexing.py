"""Unit tests for indexing domain models."""

from dataclasses import FrozenInstanceError

import pytest

from knowledge_assistant.core.indexing import (
    ApprovalStatus,
    IndexingPreview,
    IndexingSource,
    IndexingSourceKind,
)


class TestIndexingSourceKind:
    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (IndexingSourceKind.FILE, "file"),
            (IndexingSourceKind.DIRECTORY, "directory"),
            (IndexingSourceKind.DOCUMENT_URL, "document_url"),
            (IndexingSourceKind.DIRECTORY_URL, "directory_url"),
        ],
    )
    def test_enum_members(self, member: IndexingSourceKind, value: str) -> None:
        assert member.value == value


class TestApprovalStatus:
    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (ApprovalStatus.PENDING, "pending"),
            (ApprovalStatus.APPROVED, "approved"),
            (ApprovalStatus.REJECTED, "rejected"),
        ],
    )
    def test_enum_members(self, member: ApprovalStatus, value: str) -> None:
        assert member.value == value


class TestIndexingSource:
    def test_valid_construction(self) -> None:
        source = IndexingSource(
            kind=IndexingSourceKind.FILE,
            location="docs/guide.md",
            recursive=False,
        )
        assert source.kind == IndexingSourceKind.FILE
        assert source.location == "docs/guide.md"
        assert source.recursive is False

    def test_location_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="location must be non-empty"):
            IndexingSource(
                kind=IndexingSourceKind.DIRECTORY,
                location="   ",
                recursive=True,
            )

    @pytest.mark.parametrize(
        "kind",
        [IndexingSourceKind.FILE, IndexingSourceKind.DOCUMENT_URL],
    )
    def test_recursive_must_be_false_for_file_and_document_url(
        self,
        kind: IndexingSourceKind,
    ) -> None:
        with pytest.raises(
            ValueError,
            match=r"recursive must be False for FILE and DOCUMENT_URL sources",
        ):
            IndexingSource(
                kind=kind,
                location="docs/guide.md",
                recursive=True,
            )

    def test_immutability(self) -> None:
        source = IndexingSource(
            kind=IndexingSourceKind.FILE,
            location="docs/guide.md",
            recursive=False,
        )
        with pytest.raises(FrozenInstanceError):
            source.location = "other"  # type: ignore[misc]


class TestIndexingPreview:
    @pytest.fixture
    def source(self) -> IndexingSource:
        return IndexingSource(
            kind=IndexingSourceKind.DIRECTORY,
            location="docs/",
            recursive=True,
        )

    def test_valid_construction(self, source: IndexingSource) -> None:
        preview = IndexingPreview(
            sources=(source,),
            document_count=10,
            chunk_count=50,
            replaces_existing=True,
        )
        assert preview.sources == (source,)
        assert preview.document_count == 10
        assert preview.chunk_count == 50
        assert preview.replaces_existing is True

    @pytest.mark.parametrize("field_name", ["document_count", "chunk_count"])
    def test_counts_must_be_non_negative(
        self,
        source: IndexingSource,
        field_name: str,
    ) -> None:
        values = {
            "sources": (source,),
            "document_count": 1,
            "chunk_count": 1,
            "replaces_existing": False,
        }
        values[field_name] = -1
        with pytest.raises(ValueError, match="must be >= 0"):
            IndexingPreview(**values)  # type: ignore[arg-type]

    def test_sources_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="sources must be non-empty"):
            IndexingPreview(
                sources=(),
                document_count=0,
                chunk_count=0,
                replaces_existing=False,
            )

    def test_immutability(self, source: IndexingSource) -> None:
        preview = IndexingPreview(
            sources=(source,),
            document_count=1,
            chunk_count=1,
            replaces_existing=False,
        )
        with pytest.raises(FrozenInstanceError):
            preview.document_count = 2  # type: ignore[misc]
