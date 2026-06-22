"""
Hybrid retrieval for the knowledge assistant.

Dense and sparse leaf retrievers orchestrate query embedding and vector search.
FusionRetriever composes leaf retrievers with reciprocal rank fusion.
RerankRetriever composes any base retriever with deterministic reranking.
"""

from knowledge_assistant.retrieval.config import (
    BgeRerankerSettings,
    DenseRetrievalSettings,
    FusionRetrievalSettings,
    RerankerMode,
    RerankRetrievalSettings,
    parse_reranker_mode,
)
from knowledge_assistant.retrieval.dense import DenseRetriever
from knowledge_assistant.retrieval.embeddings import (
    BgeM3QueryEmbeddingProvider,
    BgeM3SparseQueryEmbeddingProvider,
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
from knowledge_assistant.retrieval.rerank import (
    BgeReranker,
    BgeRerankerBackend,
    BgeRerankerModelLoader,
    Reranker,
    RerankRetriever,
    StubReranker,
)
from knowledge_assistant.retrieval.sparse import SparseRetriever

__all__ = [
    "BgeReranker",
    "BgeRerankerBackend",
    "BgeRerankerModelLoader",
    "BgeRerankerSettings",
    "DenseRetrievalSettings",
    "DenseRetriever",
    "EmbeddingDimensionError",
    "FusionRetrievalSettings",
    "FusionRetriever",
    "BgeM3QueryEmbeddingProvider",
    "BgeM3SparseQueryEmbeddingProvider",
    "QueryEmbeddingProvider",
    "RerankerMode",
    "parse_reranker_mode",
    "RerankRetrievalSettings",
    "RerankRetriever",
    "Reranker",
    "RetrievalConfigurationError",
    "RetrievalError",
    "Retriever",
    "SparseQueryEmbeddingProvider",
    "SparseRetriever",
    "SparseVectorValidationError",
    "StubQueryEmbeddingProvider",
    "StubReranker",
    "StubSparseQueryEmbeddingProvider",
]
