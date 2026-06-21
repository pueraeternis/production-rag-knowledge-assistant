"""Unit tests for storage boundary models."""

import pytest

from knowledge_assistant.storage.models import SparseVector


class TestSparseVector:
    def test_valid_construction(self) -> None:
        vector = SparseVector(indices=(0, 2, 5), values=(0.1, 0.2, 0.3))
        assert vector.indices == (0, 2, 5)
        assert vector.values == (0.1, 0.2, 0.3)

    def test_rejects_mismatched_lengths(self) -> None:
        with pytest.raises(
            ValueError,
            match="indices and values must have the same length",
        ):
            SparseVector(indices=(0, 1), values=(0.5,))

    def test_rejects_duplicate_indices(self) -> None:
        with pytest.raises(ValueError, match="indices must be unique"):
            SparseVector(indices=(0, 0), values=(0.5, 0.3))

    @pytest.mark.parametrize("index", [-1, -10])
    def test_rejects_negative_indices(self, index: int) -> None:
        with pytest.raises(ValueError, match="indices must be >= 0"):
            SparseVector(indices=(index,), values=(0.5,))
