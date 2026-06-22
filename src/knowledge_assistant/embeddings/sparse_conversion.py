"""Lexical weight conversion for BGE-M3 sparse embeddings."""

from __future__ import annotations

import math
from collections.abc import Mapping

from knowledge_assistant.embeddings.exceptions import EmbeddingRuntimeError

SparseVectorPayload = tuple[tuple[int, ...], tuple[float, ...]]


def lexical_weights_to_sparse_payload(
    weights: Mapping[int | str, float],
) -> SparseVectorPayload:
    """Convert FlagEmbedding lexical weights to sorted unique index/value tuples."""
    aggregated: dict[int, float] = {}
    for raw_key, raw_weight in weights.items():
        index = raw_key if isinstance(raw_key, int) else int(raw_key)

        weight = float(raw_weight)
        if not math.isfinite(weight) or weight <= 0:
            continue

        aggregated[index] = aggregated.get(index, 0.0) + weight

    if not aggregated:
        msg = "lexical weights produced no non-zero sparse entries"
        raise EmbeddingRuntimeError(msg)

    indices = tuple(sorted(aggregated))
    values = tuple(aggregated[index] for index in indices)
    return indices, values
