"""Storage boundary types for vector persistence."""

from dataclasses import dataclass

from knowledge_assistant.core.chunk import Chunk
from knowledge_assistant.core.document import DocumentMetadata


@dataclass(frozen=True, slots=True)
class SparseVector:
    """Lexical sparse embedding passed to storage by the indexing layer."""

    indices: tuple[int, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.indices) != len(self.values):
            msg = "indices and values must have the same length"
            raise ValueError(msg)
        if len(set(self.indices)) != len(self.indices):
            msg = "indices must be unique"
            raise ValueError(msg)
        if any(index < 0 for index in self.indices):
            msg = "indices must be >= 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ChunkUpsertItem:
    """Write model combining domain chunk data with pre-computed vectors."""

    chunk: Chunk
    document_metadata: DocumentMetadata
    dense_vector: tuple[float, ...]
    sparse_vector: SparseVector
