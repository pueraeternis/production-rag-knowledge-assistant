"""Retrieval query and result models."""

from dataclasses import dataclass

from knowledge_assistant.core.chunk import Chunk


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Input to the retrieval layer."""

    text: str
    top_k: int

    def __post_init__(self) -> None:
        if not self.text.strip():
            msg = "text must be non-empty"
            raise ValueError(msg)
        if self.top_k < 1:
            msg = "top_k must be >= 1"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single retrieved chunk with ranking score."""

    chunk: Chunk
    score: float


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Aggregate output of a retrieval operation."""

    query: SearchQuery
    results: tuple[SearchResult, ...]

    def __post_init__(self) -> None:
        if len(self.results) > self.query.top_k:
            msg = "results length must be <= query.top_k"
            raise ValueError(msg)
