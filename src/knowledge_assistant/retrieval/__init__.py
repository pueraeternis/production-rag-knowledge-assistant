"""Hybrid retrieval, fusion, and reranking for the knowledge assistant."""

from knowledge_assistant.retrieval.config import DenseRetrievalSettings
from knowledge_assistant.retrieval.dense import DenseRetriever
from knowledge_assistant.retrieval.embeddings import (
    QueryEmbeddingProvider,
    StubQueryEmbeddingProvider,
)
from knowledge_assistant.retrieval.exceptions import (
    EmbeddingDimensionError,
    RetrievalConfigurationError,
    RetrievalError,
)

__all__ = [
    "DenseRetrievalSettings",
    "DenseRetriever",
    "EmbeddingDimensionError",
    "QueryEmbeddingProvider",
    "RetrievalConfigurationError",
    "RetrievalError",
    "StubQueryEmbeddingProvider",
]
