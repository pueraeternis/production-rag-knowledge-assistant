"""Unit tests for sparse search input validation."""

import math

import pytest

from knowledge_assistant.storage.validation import validate_sparse_search_input


class TestValidateSparseSearchInput:
    def test_accepts_valid_input(self) -> None:
        validate_sparse_search_input((0, 2, 5), (0.5, 0.3, 0.2))

    def test_rejects_length_mismatch(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            validate_sparse_search_input((0, 1), (0.5,))

    def test_rejects_duplicate_indices(self) -> None:
        with pytest.raises(ValueError, match="unique"):
            validate_sparse_search_input((0, 0), (0.5, 0.5))

    def test_rejects_negative_indices(self) -> None:
        with pytest.raises(ValueError, match=">= 0"):
            validate_sparse_search_input((-1,), (0.5,))

    def test_rejects_non_finite_values(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            validate_sparse_search_input((0,), (math.nan,))

    def test_allows_empty_input(self) -> None:
        validate_sparse_search_input((), ())
