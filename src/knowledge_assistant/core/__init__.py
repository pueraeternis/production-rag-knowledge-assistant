"""Shared domain types for the knowledge assistant."""

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.document import (
    Document,
    DocumentContent,
    DocumentMetadata,
)
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.indexing import (
    ApprovalStatus,
    IndexingPreview,
    IndexingSource,
    IndexingSourceKind,
)
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.core.source import LineRange, SourceReference

__all__ = [
    "ApprovalStatus",
    "Chunk",
    "ChunkId",
    "ChunkMetadata",
    "Document",
    "DocumentContent",
    "DocumentId",
    "DocumentMetadata",
    "IndexingPreview",
    "IndexingSource",
    "IndexingSourceKind",
    "LineRange",
    "RetrievalResult",
    "SearchQuery",
    "SearchResult",
    "SourceReference",
]
