"""Retrieval evaluation layer."""

from knowledge_assistant.evaluation.dataset import (
    DocumentRegistry,
    EvaluationCase,
    EvaluationDataset,
    load_evaluation_dataset,
)
from knowledge_assistant.evaluation.report import (
    ComparisonReport,
    EvaluationCaseResult,
    EvaluationReport,
    compare_evaluation_reports,
    format_comparison_report,
    format_evaluation_report,
)
from knowledge_assistant.evaluation.runner import EvaluationRunner
from knowledge_assistant.evaluation.settings import EvaluationSettings

__all__ = [
    "ComparisonReport",
    "DocumentRegistry",
    "EvaluationCase",
    "EvaluationCaseResult",
    "EvaluationDataset",
    "EvaluationReport",
    "EvaluationRunner",
    "EvaluationSettings",
    "compare_evaluation_reports",
    "format_comparison_report",
    "format_evaluation_report",
    "load_evaluation_dataset",
]
