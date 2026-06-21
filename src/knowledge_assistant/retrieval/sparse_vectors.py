"""Retrieval-local sparse query vector representation."""

from __future__ import annotations

import math
from dataclasses import dataclass

from knowledge_assistant.retrieval.exceptions import SparseVectorValidationError


@dataclass(frozen=True, slots=True)
class SparseQueryVector:
    """Validated sparse embedding for a search query on the read path."""

    indices: tuple[int, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.indices) != len(self.values):
            msg = "indices and values must have the same length"
            raise SparseVectorValidationError(msg)
        if len(set(self.indices)) != len(self.indices):
            msg = "indices must be unique"
            raise SparseVectorValidationError(msg)
        if any(index < 0 for index in self.indices):
            msg = "indices must be >= 0"
            raise SparseVectorValidationError(msg)
        if len(self.indices) < 1:
            msg = "sparse query vector must be non-empty"
            raise SparseVectorValidationError(msg)
        if any(not math.isfinite(value) for value in self.values):
            msg = "values must be finite"
            raise SparseVectorValidationError(msg)
