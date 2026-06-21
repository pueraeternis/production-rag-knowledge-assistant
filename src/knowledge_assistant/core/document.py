"""Document entity and metadata models."""

from dataclasses import dataclass

from knowledge_assistant.core.identifiers import DocumentId


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """Descriptive metadata for a knowledge-base document."""

    title: str
    path: str
    source_uri: str | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            msg = "title must be non-empty"
            raise ValueError(msg)
        if not self.path.strip():
            msg = "path must be non-empty"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Document:
    """Document entity with metadata; does not carry loaded content."""

    document_id: DocumentId
    metadata: DocumentMetadata

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            msg = "document_id must be non-empty"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class DocumentContent:
    """Full document text payload, separate from entity metadata."""

    document_id: DocumentId
    content: str

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            msg = "document_id must be non-empty"
            raise ValueError(msg)
