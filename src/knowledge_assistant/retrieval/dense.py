"""Dense retrieval orchestration."""

from knowledge_assistant.core.retrieval import RetrievalResult, SearchQuery
from knowledge_assistant.retrieval.config import DenseRetrievalSettings
from knowledge_assistant.retrieval.embeddings import QueryEmbeddingProvider
from knowledge_assistant.retrieval.exceptions import EmbeddingDimensionError
from knowledge_assistant.storage.protocol import VectorStore


class DenseRetriever:
    """Orchestrates query embedding and dense vector search."""

    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedding_provider: QueryEmbeddingProvider,
        settings: DenseRetrievalSettings,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._settings = settings

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        """Embed the query text, search dense vectors, and return ranked results."""
        vector = self._embedding_provider.embed_query(query.text)
        expected_dimension = self._settings.dense_vector_size
        if len(vector) != expected_dimension:
            msg = (
                f"embedding dimension {len(vector)} does not match "
                f"expected {expected_dimension}"
            )
            raise EmbeddingDimensionError(msg)

        search_results = self._vector_store.search_dense(
            vector=vector,
            top_k=query.top_k,
        )
        if len(search_results) > query.top_k:
            search_results = search_results[: query.top_k]

        return RetrievalResult(query=query, results=search_results)
