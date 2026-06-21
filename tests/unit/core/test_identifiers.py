"""Unit tests for typed identifiers."""

from knowledge_assistant.core.identifiers import ChunkId, DocumentId


def test_document_id_is_distinct_newtype() -> None:
    doc_id = DocumentId("doc-1")
    assert doc_id == "doc-1"
    assert isinstance(doc_id, str)


def test_chunk_id_is_distinct_newtype() -> None:
    chunk_id = ChunkId("chunk-1")
    assert chunk_id == "chunk-1"
    assert isinstance(chunk_id, str)
