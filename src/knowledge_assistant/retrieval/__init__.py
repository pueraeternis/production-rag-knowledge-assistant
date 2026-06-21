"""Hybrid retrieval for the knowledge assistant.

Dense and sparse leaf retrievers orchestrate query embedding and vector search.
Fusion and reranking are deferred to later plans.
"""

from knowledge_assistant.retrieval.config import DenseRetrievalSettings
from knowledge_assistant.retrieval.dense import DenseRetriever
from knowledge_assistant.retrieval.embeddings import (
    QueryEmbeddingProvider,
    SparseQueryEmbeddingProvider,
    StubQueryEmbeddingProvider,
    StubSparseQueryEmbeddingProvider,
)
from knowledge_assistant.retrieval.exceptions import (
    EmbeddingDimensionError,
    RetrievalConfigurationError,
    RetrievalError,
    SparseVectorValidationError,
)
from knowledge_assistant.retrieval.sparse import SparseRetriever

__all__ = [
    "DenseRetrievalSettings",
    "DenseRetriever",
    "EmbeddingDimensionError",
    "QueryEmbeddingProvider",
    "RetrievalConfigurationError",
    "RetrievalError",
    "SparseQueryEmbeddingProvider",
    "SparseRetriever",
    "SparseVectorValidationError",
    "StubQueryEmbeddingProvider",
    "StubSparseQueryEmbeddingProvider",
]
