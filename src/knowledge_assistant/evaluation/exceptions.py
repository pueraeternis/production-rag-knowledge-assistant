"""Evaluation layer error types."""


class EvaluationError(Exception):
    """Base error for evaluation layer failures."""


class EvaluationDatasetError(EvaluationError):
    """Invalid or malformed evaluation dataset."""
