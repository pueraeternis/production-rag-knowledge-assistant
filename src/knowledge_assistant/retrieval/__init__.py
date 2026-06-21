"""Hybrid retrieval for the knowledge assistant.

Dense and sparse leaf retrievers orchestrate query embedding and vector search.
FusionRetriever composes leaf retrievers with reciprocal rank fusion.
Reranking is deferred to a later plan.
"""

from knowledge_assistant.retrieval.config import (
    DenseRetrievalSettings,
    FusionRetrievalSettings,
)
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
from knowledge_assistant.retrieval.fusion import FusionRetriever
from knowledge_assistant.retrieval.protocol import Retriever
from knowledge_assistant.retrieval.sparse import SparseRetriever

__all__ = [
    "DenseRetrievalSettings",
    "DenseRetriever",
    "EmbeddingDimensionError",
    "FusionRetrievalSettings",
    "FusionRetriever",
    "QueryEmbeddingProvider",
    "Retriever",
    "RetrievalConfigurationError",
    "RetrievalError",
    "SparseQueryEmbeddingProvider",
    "SparseRetriever",
    "SparseVectorValidationError",
    "StubQueryEmbeddingProvider",
    "StubSparseQueryEmbeddingProvider",
]
