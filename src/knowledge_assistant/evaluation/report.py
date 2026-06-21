"""Evaluation report models, comparison assembly, and text formatters."""

from __future__ import annotations

from dataclasses import dataclass

from knowledge_assistant.evaluation.exceptions import EvaluationError


@dataclass(frozen=True, slots=True)
class EvaluationCaseResult:
    """Per-case retrieval evaluation outcome."""

    case_id: str
    question: str
    expected_document_key: str
    expected_document_path: str
    hit_at_k: dict[int, bool]
    reciprocal_rank: float
    first_hit_rank: int | None
    retrieved_document_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Aggregated retrieval evaluation for one retriever strategy."""

    retriever_label: str
    dataset_id: str
    eval_top_k: int
    metrics_k: tuple[int, ...]
    case_count: int
    hit_rate_at_k: dict[int, float]
    recall_at_k: dict[int, float]
    mrr: float
    cases: tuple[EvaluationCaseResult, ...]

    def __post_init__(self) -> None:
        if not self.retriever_label.strip():
            msg = "retriever_label must be non-empty"
            raise ValueError(msg)
        if self.case_count != len(self.cases):
            msg = "case_count must match number of case results"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    """Side-by-side retrieval strategy comparison."""

    dataset_id: str
    eval_top_k: int
    metrics_k: tuple[int, ...]
    strategies: tuple[str, ...]
    hit_rate_at_k: dict[int, tuple[float, ...]]
    recall_at_k: dict[int, tuple[float, ...]]
    mrr: tuple[float, ...]
    reports: tuple[EvaluationReport, ...]

    def __post_init__(self) -> None:
        if len(self.strategies) < 2:
            msg = "comparison requires at least two strategies"
            raise ValueError(msg)
        if len(self.strategies) != len(self.reports):
            msg = "strategies length must match reports length"
            raise ValueError(msg)
        for metric_values in self.hit_rate_at_k.values():
            if len(metric_values) != len(self.strategies):
                msg = "hit_rate_at_k vectors must match strategy count"
                raise ValueError(msg)
        for metric_values in self.recall_at_k.values():
            if len(metric_values) != len(self.strategies):
                msg = "recall_at_k vectors must match strategy count"
                raise ValueError(msg)
        if len(self.mrr) != len(self.strategies):
            msg = "mrr vector must match strategy count"
            raise ValueError(msg)


def compare_evaluation_reports(
    reports: tuple[EvaluationReport, ...],
) -> ComparisonReport:
    """Assemble a comparison report from compatible single-strategy reports."""
    if len(reports) < 2:
        msg = "compare_evaluation_reports requires at least two reports"
        raise EvaluationError(msg)

    first = reports[0]
    for report in reports[1:]:
        if report.dataset_id != first.dataset_id:
            msg = "reports must share the same dataset_id"
            raise EvaluationError(msg)
        if report.eval_top_k != first.eval_top_k:
            msg = "reports must share the same eval_top_k"
            raise EvaluationError(msg)
        if report.metrics_k != first.metrics_k:
            msg = "reports must share the same metrics_k"
            raise EvaluationError(msg)
        if report.case_count != first.case_count:
            msg = "reports must share the same case_count"
            raise EvaluationError(msg)

    strategies = tuple(report.retriever_label for report in reports)
    hit_rate_at_k = {
        k: tuple(report.hit_rate_at_k[k] for report in reports) for k in first.metrics_k
    }
    recall_at_k = {
        k: tuple(report.recall_at_k[k] for report in reports) for k in first.metrics_k
    }
    mrr = tuple(report.mrr for report in reports)

    return ComparisonReport(
        dataset_id=first.dataset_id,
        eval_top_k=first.eval_top_k,
        metrics_k=first.metrics_k,
        strategies=strategies,
        hit_rate_at_k=hit_rate_at_k,
        recall_at_k=recall_at_k,
        mrr=mrr,
        reports=reports,
    )


def _format_metric_row(
    label: str,
    values: tuple[float, ...],
    *,
    column_widths: tuple[int, ...],
) -> str:
    cells = [label.ljust(column_widths[0])]
    for index, value in enumerate(values):
        cells.append(f"{value:.3f}".rjust(column_widths[index + 1]))
    return "  ".join(cells)


def format_evaluation_report(report: EvaluationReport) -> str:
    """Format a single-strategy evaluation report as plain text."""
    lines = [
        f"Evaluation Report: {report.retriever_label}",
        f"Dataset: {report.dataset_id}",
        f"Cases: {report.case_count}",
        f"Eval top_k: {report.eval_top_k}",
        "",
        "Aggregate Metrics:",
    ]
    for k in report.metrics_k:
        hit = report.hit_rate_at_k[k]
        recall = report.recall_at_k[k]
        lines.append(f"  Hit@{k}: {hit:.3f}  Recall@{k}: {recall:.3f}")
    lines.append(f"  MRR: {report.mrr:.3f}")
    return "\n".join(lines)


def format_comparison_report(comparison: ComparisonReport) -> str:
    """Format a multi-strategy comparison report as a plain-text table."""
    metric_label_width = 12
    strategy_widths = tuple(max(len(strategy), 7) for strategy in comparison.strategies)
    column_widths = (metric_label_width, *strategy_widths)

    header_cells = ["Metric".ljust(metric_label_width)]
    for index, strategy in enumerate(comparison.strategies):
        header_cells.append(strategy.rjust(strategy_widths[index]))
    lines = [
        f"Comparison Report: {comparison.dataset_id}",
        f"Cases: {comparison.reports[0].case_count}",
        f"Eval top_k: {comparison.eval_top_k}",
        "",
        "  ".join(header_cells),
    ]

    for k in comparison.metrics_k:
        lines.append(
            _format_metric_row(
                f"Hit@{k}",
                comparison.hit_rate_at_k[k],
                column_widths=column_widths,
            ),
        )
        lines.append(
            _format_metric_row(
                f"Recall@{k}",
                comparison.recall_at_k[k],
                column_widths=column_widths,
            ),
        )
    lines.append(_format_metric_row("MRR", comparison.mrr, column_widths=column_widths))
    return "\n".join(lines)
