"""Indexing source and human-approval models."""

from dataclasses import dataclass
from enum import Enum


class IndexingSourceKind(Enum):
    """Category of an indexing source."""

    FILE = "file"
    DIRECTORY = "directory"
    DOCUMENT_URL = "document_url"
    DIRECTORY_URL = "directory_url"


class ApprovalStatus(Enum):
    """Human-in-the-loop decision for destructive indexing operations."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class IndexingSource:
    """Describes where documents originate for indexing."""

    kind: IndexingSourceKind
    location: str
    recursive: bool

    def __post_init__(self) -> None:
        if not self.location.strip():
            msg = "location must be non-empty"
            raise ValueError(msg)
        if self.recursive and self.kind in (
            IndexingSourceKind.FILE,
            IndexingSourceKind.DOCUMENT_URL,
        ):
            msg = "recursive must be False for FILE and DOCUMENT_URL sources"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class IndexingPreview:
    """Summary shown before human approval of index changes."""

    sources: tuple[IndexingSource, ...]
    document_count: int
    chunk_count: int
    replaces_existing: bool

    def __post_init__(self) -> None:
        if self.document_count < 0:
            msg = "document_count must be >= 0"
            raise ValueError(msg)
        if self.chunk_count < 0:
            msg = "chunk_count must be >= 0"
            raise ValueError(msg)
        if not self.sources:
            msg = "sources must be non-empty"
            raise ValueError(msg)
