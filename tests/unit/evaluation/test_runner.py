"""Unit tests for EvaluationRunner."""

from pathlib import Path

import pytest

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.evaluation.dataset import load_evaluation_dataset
from knowledge_assistant.evaluation.runner import EvaluationRunner
from knowledge_assistant.evaluation.settings import EvaluationSettings

FIXTURE_PATH = Path("tests/unit/evaluation/fixtures/minimal_dataset.json")


def _make_search_result(
    *,
    chunk_id: str,
    document_path: str,
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
        score=0.5,
        source=SourceReference(
            document_title="Title",
            document_path=document_path,
            section_title="Section",
            line_range=LineRange(start_line=1, end_line=5),
        ),
    )


class FakeRetriever:
    """Returns scripted results keyed by query text."""

    def __init__(
        self,
        *,
        responses: dict[str, tuple[SearchResult, ...]],
    ) -> None:
        self._responses = responses
        self.calls: list[SearchQuery] = []

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        self.calls.append(query)
        results = self._responses.get(query.text, ())
        return RetrievalResult(query=query, results=results)


class TestEvaluationRunner:
    def test_run_aggregates_metrics_with_fake_retriever(self) -> None:
        dataset = load_evaluation_dataset(FIXTURE_PATH)
        retriever = FakeRetriever(
            responses={
                "What is policy A about?": (
                    _make_search_result(
                        chunk_id="a1",
                        document_path="knowledge/policies/policy_a.md",
                    ),
                ),
                "What is policy B about?": (
                    _make_search_result(
                        chunk_id="b1",
                        document_path="knowledge/policies/travel_policy.md",
                    ),
                    _make_search_result(
                        chunk_id="b2",
                        document_path="knowledge/policies/policy_b.md",
                    ),
                ),
            },
        )
        runner = EvaluationRunner(EvaluationSettings(eval_top_k=5, metrics_k=(1, 3, 5)))

        report = runner.run(retriever, dataset, retriever_label="dense")

        assert report.retriever_label == "dense"
        assert report.case_count == 2
        assert report.hit_rate_at_k[1] == 0.5
        assert report.hit_rate_at_k[3] == 1.0
        assert report.recall_at_k[1] == 0.5
        assert report.mrr == pytest.approx(0.75)
        assert all(call.top_k == 5 for call in retriever.calls)

    def test_rejects_empty_retriever_label(self) -> None:
        dataset = load_evaluation_dataset(FIXTURE_PATH)
        runner = EvaluationRunner(EvaluationSettings())

        with pytest.raises(ValueError, match="retriever_label"):
            runner.run(FakeRetriever(responses={}), dataset, retriever_label="  ")

    def test_propagates_retriever_exceptions(self) -> None:
        dataset = load_evaluation_dataset(FIXTURE_PATH)

        class ExplodingRetriever:
            def retrieve(self, query: SearchQuery) -> RetrievalResult:
                _ = query
                raise RuntimeError("retriever failed")

        runner = EvaluationRunner(EvaluationSettings())

        with pytest.raises(RuntimeError, match="retriever failed"):
            runner.run(ExplodingRetriever(), dataset, retriever_label="dense")
