"""Optional smoke tests for the real BGE reranker runtime."""

import os

import pytest

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import SearchQuery, SearchResult
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.retrieval import BgeReranker, BgeRerankerSettings


def _enabled() -> bool:
    return os.environ.get("RAG_RERANKER_ENABLE_REAL_TESTS", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


pytestmark = [
    pytest.mark.real_model,
    pytest.mark.skipif(
        not _enabled(),
        reason="set RAG_RERANKER_ENABLE_REAL_TESTS=true to load the real reranker",
    ),
]


def _source() -> SourceReference:
    return SourceReference(
        document_title="Guide",
        document_path="docs/guide.md",
        section_title="Overview",
        line_range=LineRange(start_line=1, end_line=3),
    )


def _result(chunk_id: str, text: str) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=ChunkId(chunk_id),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Overview",
                line_range=LineRange(start_line=1, end_line=3),
                chunk_index=0,
            ),
            text=text,
        ),
        score=0.0,
        source=_source(),
    )


def test_bge_reranker_preserves_candidate_count_with_real_runtime() -> None:
    settings = BgeRerankerSettings.from_env(device="cpu", use_fp16=False)
    reranker = BgeReranker(settings=settings)
    candidates = (
        _result("chunk-a", "Remote work policy allows manager-approved hybrid work."),
        _result("chunk-b", "Travel expenses require receipts."),
    )

    reranked = reranker.rerank(
        SearchQuery(text="What is the remote work policy?", top_k=2),
        candidates,
    )

    assert len(reranked) == len(candidates)
    assert all(isinstance(result.score, float) for result in reranked)
