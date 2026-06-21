"""Unit tests for evaluation report formatting."""

from knowledge_assistant.evaluation.report import (
    EvaluationCaseResult,
    EvaluationReport,
    format_evaluation_report,
)


def _make_report(*, label: str, mrr: float) -> EvaluationReport:
    case = EvaluationCaseResult(
        case_id="case-1",
        question="Question?",
        expected_document_key="policy-a",
        expected_document_path="knowledge/policies/policy_a.md",
        hit_at_k={1: True, 3: True, 5: True},
        reciprocal_rank=1.0,
        first_hit_rank=1,
        retrieved_document_paths=("knowledge/policies/policy_a.md",),
    )
    return EvaluationReport(
        retriever_label=label,
        dataset_id="fixture_dataset",
        eval_top_k=5,
        metrics_k=(1, 3, 5),
        case_count=1,
        hit_rate_at_k={1: 1.0, 3: 1.0, 5: 1.0},
        recall_at_k={1: 1.0, 3: 1.0, 5: 1.0},
        mrr=mrr,
        cases=(case,),
    )


class TestFormatEvaluationReport:
    def test_produces_stable_plain_text(self) -> None:
        report = _make_report(label="dense", mrr=1.0)

        text = format_evaluation_report(report)

        assert text == (
            "Evaluation Report: dense\n"
            "Dataset: fixture_dataset\n"
            "Cases: 1\n"
            "Eval top_k: 5\n"
            "\n"
            "Aggregate Metrics:\n"
            "  Hit@1: 1.000  Recall@1: 1.000\n"
            "  Hit@3: 1.000  Recall@3: 1.000\n"
            "  Hit@5: 1.000  Recall@5: 1.000\n"
            "  MRR: 1.000"
        )
