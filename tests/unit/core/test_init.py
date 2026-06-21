"""Unit tests for core public API exports."""

from knowledge_assistant import core


def test_public_api_exports() -> None:
    expected = {
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
    }
    assert set(core.__all__) == expected
    for name in expected:
        assert hasattr(core, name)
