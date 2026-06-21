"""Chunk entity and structural metadata models."""

from dataclasses import dataclass

from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.source import LineRange


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    """Positional and structural metadata for an indexed chunk."""

    document_id: DocumentId
    section_title: str
    line_range: LineRange
    chunk_index: int

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            msg = "document_id must be non-empty"
            raise ValueError(msg)
        if self.chunk_index < 0:
            msg = "chunk_index must be >= 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Chunk:
    """An indexed fragment of a document."""

    chunk_id: ChunkId
    metadata: ChunkMetadata
    text: str

    def __post_init__(self) -> None:
        if not self.chunk_id.strip():
            msg = "chunk_id must be non-empty"
            raise ValueError(msg)
        if not self.text.strip():
            msg = "text must be non-empty"
            raise ValueError(msg)
