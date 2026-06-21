"""Indexing configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndexingSettings:
    """Configuration for document loading, chunking, and embedding dimensions."""

    chunk_size: int = 1024
    chunk_overlap: int = 128
    dense_vector_size: int = 1024
    supported_extensions: tuple[str, ...] = (".md", ".txt")

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            msg = "chunk_size must be > 0"
            raise ValueError(msg)
        if self.chunk_overlap < 0:
            msg = "chunk_overlap must be >= 0"
            raise ValueError(msg)
        if self.chunk_overlap >= self.chunk_size:
            msg = "chunk_overlap must be < chunk_size"
            raise ValueError(msg)
        if self.dense_vector_size <= 0:
            msg = "dense_vector_size must be > 0"
            raise ValueError(msg)
