"""Unit tests for multi-strategy comparison assembly."""

import pytest

from knowledge_assistant.evaluation.exceptions import EvaluationError
from knowledge_assistant.evaluation.report import (
    ComparisonReport,
    EvaluationCaseResult,
    EvaluationReport,
    compare_evaluation_reports,
    format_comparison_report,
)


def _make_case_result(*, hit_at_1: bool) -> EvaluationCaseResult:
    return EvaluationCaseResult(
        case_id="case-1",
        question="Question?",
        expected_document_key="policy-a",
        expected_document_path="knowledge/policies/policy_a.md",
        hit_at_k={1: hit_at_1, 3: hit_at_1, 5: hit_at_1},
        reciprocal_rank=1.0 if hit_at_1 else 0.0,
        first_hit_rank=1 if hit_at_1 else None,
        retrieved_document_paths=("knowledge/policies/policy_a.md",),
    )


def _make_report(
    *,
    label: str,
    hit_at_1: float,
    mrr: float,
) -> EvaluationReport:
    case = _make_case_result(hit_at_1=hit_at_1 == 1.0)
    return EvaluationReport(
        retriever_label=label,
        dataset_id="fixture_dataset",
        eval_top_k=5,
        metrics_k=(1, 3, 5),
        case_count=1,
        hit_rate_at_k={1: hit_at_1, 3: hit_at_1, 5: hit_at_1},
        recall_at_k={1: hit_at_1, 3: hit_at_1, 5: hit_at_1},
        mrr=mrr,
        cases=(case,),
    )


class TestCompareEvaluationReports:
    def test_builds_comparison_report(self) -> None:
        reports = (
            _make_report(label="dense", hit_at_1=1.0, mrr=1.0),
            _make_report(label="sparse", hit_at_1=0.0, mrr=0.0),
        )

        comparison = compare_evaluation_reports(reports)

        assert comparison.strategies == ("dense", "sparse")
        assert comparison.hit_rate_at_k[1] == (1.0, 0.0)
        assert comparison.mrr == (1.0, 0.0)
        assert len(comparison.reports) == 2

    def test_requires_at_least_two_reports(self) -> None:
        report = _make_report(label="dense", hit_at_1=1.0, mrr=1.0)

        with pytest.raises(EvaluationError, match="at least two reports"):
            compare_evaluation_reports((report,))

    def test_rejects_mismatched_dataset_id(self) -> None:
        dense = _make_report(label="dense", hit_at_1=1.0, mrr=1.0)
        sparse = _make_report(label="sparse", hit_at_1=0.0, mrr=0.0)
        sparse_mismatch = EvaluationReport(
            retriever_label=sparse.retriever_label,
            dataset_id="other_dataset",
            eval_top_k=sparse.eval_top_k,
            metrics_k=sparse.metrics_k,
            case_count=sparse.case_count,
            hit_rate_at_k=sparse.hit_rate_at_k,
            recall_at_k=sparse.recall_at_k,
            mrr=sparse.mrr,
            cases=sparse.cases,
        )

        with pytest.raises(EvaluationError, match="dataset_id"):
            compare_evaluation_reports((dense, sparse_mismatch))


class TestFormatComparisonReport:
    def test_produces_side_by_side_table(self) -> None:
        comparison = compare_evaluation_reports(
            (
                _make_report(label="dense", hit_at_1=1.0, mrr=1.0),
                _make_report(label="sparse", hit_at_1=0.0, mrr=0.0),
                _make_report(label="fusion", hit_at_1=1.0, mrr=1.0),
                _make_report(label="rerank", hit_at_1=1.0, mrr=0.5),
            ),
        )

        text = format_comparison_report(comparison)

        assert "Comparison Report: fixture_dataset" in text
        assert "dense" in text
        assert "sparse" in text
        assert "fusion" in text
        assert "rerank" in text
        assert "Hit@1" in text
        assert "Recall@5" in text
        assert "MRR" in text

    def test_comparison_report_rejects_single_strategy(self) -> None:
        report = _make_report(label="dense", hit_at_1=1.0, mrr=1.0)

        with pytest.raises(ValueError, match="at least two strategies"):
            ComparisonReport(
                dataset_id=report.dataset_id,
                eval_top_k=report.eval_top_k,
                metrics_k=report.metrics_k,
                strategies=("dense",),
                hit_rate_at_k={1: (1.0,)},
                recall_at_k={1: (1.0,)},
                mrr=(1.0,),
                reports=(report,),
            )
