"""Unit tests for SparseQueryVector validation."""

import math

import pytest

from knowledge_assistant.retrieval.exceptions import SparseVectorValidationError
from knowledge_assistant.retrieval.sparse_vectors import SparseQueryVector


class TestSparseQueryVector:
    def test_accepts_valid_vector(self) -> None:
        vector = SparseQueryVector(indices=(0, 2), values=(0.6, 0.8))

        assert vector.indices == (0, 2)
        assert vector.values == (0.6, 0.8)

    def test_rejects_empty_vector(self) -> None:
        with pytest.raises(SparseVectorValidationError, match="non-empty"):
            SparseQueryVector(indices=(), values=())

    def test_rejects_length_mismatch(self) -> None:
        with pytest.raises(SparseVectorValidationError, match="same length"):
            SparseQueryVector(indices=(0, 1), values=(0.5,))

    def test_rejects_duplicate_indices(self) -> None:
        with pytest.raises(SparseVectorValidationError, match="unique"):
            SparseQueryVector(indices=(0, 0), values=(0.5, 0.5))

    def test_rejects_negative_indices(self) -> None:
        with pytest.raises(SparseVectorValidationError, match=">= 0"):
            SparseQueryVector(indices=(-1,), values=(0.5,))

    def test_rejects_non_finite_values(self) -> None:
        with pytest.raises(SparseVectorValidationError, match="finite"):
            SparseQueryVector(indices=(0,), values=(math.inf,))
