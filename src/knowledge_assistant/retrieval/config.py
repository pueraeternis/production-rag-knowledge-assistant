"""Retrieval configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DenseRetrievalSettings:
    """Configuration for dense retrieval and query embedding dimensions."""

    dense_vector_size: int = 1024

    def __post_init__(self) -> None:
        if self.dense_vector_size <= 0:
            msg = "dense_vector_size must be > 0"
            raise ValueError(msg)
