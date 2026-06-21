"""Evaluation configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvaluationSettings:
    """Metric cutoffs and retrieval depth for evaluation runs."""

    eval_top_k: int = 5
    metrics_k: tuple[int, ...] = (1, 3, 5)

    def __post_init__(self) -> None:
        if self.eval_top_k < 1:
            msg = "eval_top_k must be >= 1"
            raise ValueError(msg)
        if not self.metrics_k:
            msg = "metrics_k must be non-empty"
            raise ValueError(msg)
        for k in self.metrics_k:
            if k < 1:
                msg = "each metrics_k value must be >= 1"
                raise ValueError(msg)
            if k > self.eval_top_k:
                msg = "each metrics_k value must be <= eval_top_k"
                raise ValueError(msg)
