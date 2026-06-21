"""Unit tests for document domain models."""

from dataclasses import FrozenInstanceError

import pytest

from knowledge_assistant.core.document import (
    Document,
    DocumentContent,
    DocumentMetadata,
)
from knowledge_assistant.core.identifiers import DocumentId


class TestDocumentMetadata:
    def test_valid_construction(self) -> None:
        metadata = DocumentMetadata(
            title="Guide",
            path="docs/guide.md",
            source_uri="https://example.com/guide.md",
        )
        assert metadata.title == "Guide"
        assert metadata.path == "docs/guide.md"
        assert metadata.source_uri == "https://example.com/guide.md"

    def test_source_uri_defaults_to_none(self) -> None:
        metadata = DocumentMetadata(title="Guide", path="docs/guide.md")
        assert metadata.source_uri is None

    @pytest.mark.parametrize("field_name", ["title", "path"])
    def test_required_string_fields_must_be_non_empty(self, field_name: str) -> None:
        values = {"title": "Guide", "path": "docs/guide.md"}
        values[field_name] = "   "
        with pytest.raises(ValueError, match="must be non-empty"):
            DocumentMetadata(**values)  # type: ignore[arg-type]

    def test_immutability(self) -> None:
        metadata = DocumentMetadata(title="Guide", path="docs/guide.md")
        with pytest.raises(FrozenInstanceError):
            metadata.title = "Other"  # type: ignore[misc]


class TestDocument:
    @pytest.fixture
    def metadata(self) -> DocumentMetadata:
        return DocumentMetadata(title="Guide", path="docs/guide.md")

    def test_valid_construction(self, metadata: DocumentMetadata) -> None:
        document = Document(document_id=DocumentId("doc-1"), metadata=metadata)
        assert document.document_id == DocumentId("doc-1")
        assert document.metadata == metadata

    def test_document_id_must_be_non_empty(self, metadata: DocumentMetadata) -> None:
        with pytest.raises(ValueError, match="document_id must be non-empty"):
            Document(document_id=DocumentId("   "), metadata=metadata)

    def test_immutability(self, metadata: DocumentMetadata) -> None:
        document = Document(document_id=DocumentId("doc-1"), metadata=metadata)
        with pytest.raises(FrozenInstanceError):
            document.document_id = DocumentId("doc-2")  # type: ignore[misc]


class TestDocumentContent:
    def test_valid_construction(self) -> None:
        content = DocumentContent(
            document_id=DocumentId("doc-1"),
            content="Full document text.",
        )
        assert content.document_id == DocumentId("doc-1")
        assert content.content == "Full document text."

    def test_content_may_be_empty(self) -> None:
        content = DocumentContent(document_id=DocumentId("doc-1"), content="")
        assert content.content == ""

    def test_document_id_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="document_id must be non-empty"):
            DocumentContent(document_id=DocumentId("   "), content="text")

    def test_immutability(self) -> None:
        content = DocumentContent(document_id=DocumentId("doc-1"), content="text")
        with pytest.raises(FrozenInstanceError):
            content.content = "other"  # type: ignore[misc]
