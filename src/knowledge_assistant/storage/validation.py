"""Structural validation for sparse vector search inputs."""

import math
from collections.abc import Sequence


def validate_sparse_search_input(
    indices: Sequence[int],
    values: Sequence[float],
) -> None:
    """Validate sparse search primitives. Raises ValueError on structural violation."""
    if len(indices) != len(values):
        msg = "indices and values must have the same length"
        raise ValueError(msg)
    if len(set(indices)) != len(indices):
        msg = "indices must be unique"
        raise ValueError(msg)
    if any(index < 0 for index in indices):
        msg = "indices must be >= 0"
        raise ValueError(msg)
    if any(not math.isfinite(value) for value in values):
        msg = "values must be finite"
        raise ValueError(msg)
