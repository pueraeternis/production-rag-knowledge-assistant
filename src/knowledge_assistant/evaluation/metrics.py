"""Pure retrieval metric functions for evaluation."""

from knowledge_assistant.core.retrieval import SearchResult

_BENCHMARK_CORPUS_ROOT = "knowledge/"


def normalize_document_path(path: str) -> str:
    """Normalize a document path for benchmark matching.

    Produces a canonical benchmark-relative path when the synthetic corpus
    root ``knowledge/`` appears anywhere in the input (after slash normalization
    and leading ``./`` removal). This keeps evaluation matching aligned with
    indexing, which stores absolute filesystem paths in ``SourceReference``.
    """
    normalized = path.replace("\\", "/")
    normalized = normalized.removeprefix("./")
    corpus_root_index = normalized.find(_BENCHMARK_CORPUS_ROOT)
    if corpus_root_index >= 0:
        normalized = normalized[corpus_root_index:]
    return normalized


def document_path_from_result(result: SearchResult) -> str:
    """Extract the normalized document path from a search result."""
    return normalize_document_path(result.source.document_path)


def hit_at_k(
    results: tuple[SearchResult, ...],
    *,
    expected_document_path: str,
    k: int,
) -> bool:
    """Return whether the expected document appears in the top K results."""
    if k < 1:
        msg = "k must be >= 1"
        raise ValueError(msg)
    expected = normalize_document_path(expected_document_path)
    return any(document_path_from_result(result) == expected for result in results[:k])


def recall_at_k(
    results: tuple[SearchResult, ...],
    *,
    expected_document_path: str,
    k: int,
) -> float:
    """Return recall@K for a single-relevant-document case (0.0 or 1.0 in v1)."""
    return (
        1.0
        if hit_at_k(results, expected_document_path=expected_document_path, k=k)
        else 0.0
    )


def reciprocal_rank(
    results: tuple[SearchResult, ...],
    *,
    expected_document_path: str,
) -> float:
    """Return reciprocal rank of the first matching document (0.0 if absent)."""
    expected = normalize_document_path(expected_document_path)
    for rank, result in enumerate(results, start=1):
        if document_path_from_result(result) == expected:
            return 1.0 / rank
    return 0.0
