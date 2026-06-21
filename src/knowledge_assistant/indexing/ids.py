"""Deterministic UUID5 ID generation for indexed documents and chunks."""

import hashlib
import uuid
from pathlib import Path

from knowledge_assistant.core.identifiers import ChunkId, DocumentId

INDEXING_ID_NAMESPACE = uuid.UUID("a3f2c8e1-4b5d-6e7f-8901-23456789abcd")


def normalize_source_path(path: str) -> str:
    """Resolve a path to an absolute POSIX-style string."""
    return Path(path).resolve().as_posix()


def document_id_for_path(path: str) -> DocumentId:
    """Return a stable DocumentId for a normalized source path."""
    normalized = normalize_source_path(path)
    document_uuid = uuid.uuid5(INDEXING_ID_NAMESPACE, normalized)
    document_id = str(document_uuid)
    _validate_uuid_string(document_id)
    return DocumentId(document_id)


def chunk_id_for_chunk(
    *,
    document_id: DocumentId,
    chunk_index: int,
    text: str,
) -> ChunkId:
    """Return a stable ChunkId for document scope, index, and chunk text."""
    text_digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    name = f"{document_id}|{chunk_index}|{text_digest}"
    chunk_uuid = uuid.uuid5(INDEXING_ID_NAMESPACE, name)
    chunk_id = str(chunk_uuid)
    _validate_uuid_string(chunk_id)
    return ChunkId(chunk_id)


def _validate_uuid_string(value: str) -> None:
    if not value.strip():
        msg = "generated ID must be non-empty"
        raise ValueError(msg)
    uuid.UUID(value)
