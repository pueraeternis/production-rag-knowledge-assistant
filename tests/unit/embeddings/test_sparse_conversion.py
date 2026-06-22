"""Unit tests for lexical weight to sparse payload conversion."""

import math

import pytest

from knowledge_assistant.embeddings import (
    EmbeddingRuntimeError,
    lexical_weights_to_sparse_payload,
)


class TestLexicalWeightsToSparsePayload:
    def test_sorts_indices_ascending(self) -> None:
        indices, values = lexical_weights_to_sparse_payload({30: 0.5, 10: 0.2, 20: 0.8})

        assert indices == (10, 20, 30)
        assert values == (0.2, 0.8, 0.5)

    def test_accepts_string_keys(self) -> None:
        indices, values = lexical_weights_to_sparse_payload({"42": 1.5, "7": 0.25})

        assert indices == (7, 42)
        assert values == (0.25, 1.5)

    def test_drops_zero_and_negative_weights(self) -> None:
        indices, values = lexical_weights_to_sparse_payload(
            {1: 0.0, 2: -1.0, 3: 0.5},
        )

        assert indices == (3,)
        assert values == (0.5,)

    def test_sums_duplicate_indices(self) -> None:
        indices, values = lexical_weights_to_sparse_payload({5: 0.2, "5": 0.3})

        assert indices == (5,)
        assert values[0] == pytest.approx(0.5)

    def test_rejects_non_finite_weights(self) -> None:
        indices, values = lexical_weights_to_sparse_payload(
            {1: math.nan, 2: math.inf, 3: 0.4},
        )

        assert indices == (3,)
        assert values == (0.4,)

    def test_empty_result_raises(self) -> None:
        with pytest.raises(EmbeddingRuntimeError, match="no non-zero sparse entries"):
            lexical_weights_to_sparse_payload({})

    def test_all_zero_weights_raises(self) -> None:
        with pytest.raises(EmbeddingRuntimeError, match="no non-zero sparse entries"):
            lexical_weights_to_sparse_payload({1: 0.0, 2: -0.1})
