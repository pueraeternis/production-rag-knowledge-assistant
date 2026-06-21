"""Unit tests for evaluation metric functions."""

import pytest

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import SearchResult
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.evaluation.metrics import (
    document_path_from_result,
    hit_at_k,
    normalize_document_path,
    recall_at_k,
    reciprocal_rank,
)


def make_search_result(
    *,
    chunk_id: str = "chunk-1",
    document_path: str,
    score: float = 0.5,
) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=ChunkId(chunk_id),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Section",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text="chunk text",
        ),
        score=score,
        source=SourceReference(
            document_title="Title",
            document_path=document_path,
            section_title="Section",
            line_range=LineRange(start_line=1, end_line=5),
        ),
    )


class TestNormalizeDocumentPath:
    @pytest.mark.parametrize(
        "raw_path",
        [
            "knowledge/policies/a.md",
            "./knowledge/policies/a.md",
            "knowledge\\policies\\a.md",
            "/home/user/project/knowledge/policies/a.md",
            "C:\\repo\\knowledge\\policies\\a.md",
        ],
    )
    def test_paths_normalize_to_benchmark_relative_form(self, raw_path: str) -> None:
        assert normalize_document_path(raw_path) == "knowledge/policies/a.md"

    def test_strips_leading_dot_slash(self) -> None:
        assert normalize_document_path("./knowledge/a.md") == "knowledge/a.md"

    def test_normalizes_backslashes(self) -> None:
        assert normalize_document_path("knowledge\\policies\\a.md") == (
            "knowledge/policies/a.md"
        )

    def test_non_corpus_paths_remain_relative(self) -> None:
        assert normalize_document_path("docs/guide.md") == "docs/guide.md"


class TestHitAtK:
    def test_matches_benchmark_relative_path_against_absolute_retrieval_path(
        self,
    ) -> None:
        results = (
            make_search_result(
                chunk_id="c1",
                document_path="/home/user/project/knowledge/policies/a.md",
            ),
        )
        expected = "knowledge/policies/a.md"

        assert hit_at_k(results, expected_document_path=expected, k=1) is True
        assert reciprocal_rank(results, expected_document_path=expected) == 1.0

    def test_hit_at_rank_one_for_all_k(self) -> None:
        results = (
            make_search_result(
                chunk_id="c1",
                document_path="knowledge/policies/remote_work_policy.md",
            ),
            make_search_result(
                chunk_id="c2",
                document_path="knowledge/policies/travel_policy.md",
            ),
        )
        expected = "knowledge/policies/remote_work_policy.md"

        assert hit_at_k(results, expected_document_path=expected, k=1) is True
        assert hit_at_k(results, expected_document_path=expected, k=3) is True

    def test_miss_at_one_hit_at_three(self) -> None:
        results = (
            make_search_result(
                chunk_id="c1",
                document_path="knowledge/policies/travel_policy.md",
            ),
            make_search_result(
                chunk_id="c2",
                document_path="knowledge/policies/travel_policy.md",
            ),
            make_search_result(
                chunk_id="c3",
                document_path="knowledge/policies/remote_work_policy.md",
            ),
        )
        expected = "knowledge/policies/remote_work_policy.md"

        assert hit_at_k(results, expected_document_path=expected, k=1) is False
        assert hit_at_k(results, expected_document_path=expected, k=3) is True

    def test_absent_document_is_miss(self) -> None:
        results = (
            make_search_result(
                chunk_id="c1",
                document_path="knowledge/policies/travel_policy.md",
            ),
        )
        expected = "knowledge/policies/remote_work_policy.md"

        assert hit_at_k(results, expected_document_path=expected, k=5) is False

    def test_empty_results_is_miss(self) -> None:
        assert (
            hit_at_k(
                (),
                expected_document_path="knowledge/policies/remote_work_policy.md",
                k=1,
            )
            is False
        )

    def test_multiple_chunks_same_document_count_as_one_hit(self) -> None:
        path = "knowledge/policies/remote_work_policy.md"
        results = (
            make_search_result(chunk_id="c1", document_path=path),
            make_search_result(chunk_id="c2", document_path=path),
        )

        assert hit_at_k(results, expected_document_path=path, k=2) is True
        assert reciprocal_rank(results, expected_document_path=path) == 1.0

    @pytest.mark.parametrize("k", [0, -1])
    def test_invalid_k_raises(self, k: int) -> None:
        with pytest.raises(ValueError, match="k must be >= 1"):
            hit_at_k((), expected_document_path="knowledge/a.md", k=k)


class TestRecallAtK:
    def test_recall_matches_hit_for_single_relevant_document(self) -> None:
        results = (
            make_search_result(
                chunk_id="c1",
                document_path="knowledge/policies/remote_work_policy.md",
            ),
        )
        expected = "knowledge/policies/remote_work_policy.md"

        assert recall_at_k(results, expected_document_path=expected, k=1) == 1.0
        assert recall_at_k((), expected_document_path=expected, k=1) == 0.0


class TestReciprocalRank:
    def test_rank_three_yields_one_third(self) -> None:
        results = (
            make_search_result(chunk_id="c1", document_path="knowledge/a.md"),
            make_search_result(chunk_id="c2", document_path="knowledge/b.md"),
            make_search_result(chunk_id="c3", document_path="knowledge/target.md"),
        )

        assert reciprocal_rank(
            results,
            expected_document_path="knowledge/target.md",
        ) == (1.0 / 3.0)

    def test_miss_returns_zero(self) -> None:
        results = (make_search_result(chunk_id="c1", document_path="knowledge/a.md"),)

        assert (
            reciprocal_rank(results, expected_document_path="knowledge/missing.md")
            == 0.0
        )


class TestDocumentPathFromResult:
    def test_uses_source_document_path(self) -> None:
        result = make_search_result(
            chunk_id="c1",
            document_path="./knowledge/policies/a.md",
        )

        assert document_path_from_result(result) == "knowledge/policies/a.md"
