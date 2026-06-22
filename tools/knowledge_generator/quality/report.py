"""Quality report formatting for the synthetic corpus generator."""

from __future__ import annotations

from .metrics import CorpusMetrics, QualityIssue


def format_metrics_report(metrics: CorpusMetrics) -> str:
    """Format corpus quality metrics."""
    return (
        f"Corpus quality metrics ({metrics.documents} documents):\n"
        f"  duplicate paragraphs (total): {metrics.duplicate_paragraphs}\n"
        f"  duplicate sentences (total): {metrics.duplicate_sentences}\n"
        f"  avg repeated sentence ratio: {metrics.avg_repeated_sentence_ratio:.2%}\n"
        f"  avg section title diversity: {metrics.avg_section_diversity:.2%}\n"
        f"  known filler phrase hits: {metrics.filler_hits}\n"
        f"  distinct section structures: {metrics.distinct_section_structures}"
    )


def raise_on_quality_failure(
    issues: list[QualityIssue],
    metrics: CorpusMetrics,
) -> None:
    """Raise SystemExit with a concise quality report when issues exist."""
    report = format_metrics_report(metrics)
    if not issues:
        print(report)
        print("Corpus quality gates passed.")
        return

    lines = "\n".join(f"  - {issue.path}: {issue.message}" for issue in issues[:30])
    extra = f"\n  ... and {len(issues) - 30} more" if len(issues) > 30 else ""
    raise SystemExit(
        f"{report}\nCorpus quality gate failed ({len(issues)} issues):\n{lines}{extra}",
    )
