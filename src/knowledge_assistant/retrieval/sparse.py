"""Sparse retrieval orchestration."""

from knowledge_assistant.core.retrieval import RetrievalResult, SearchQuery
from knowledge_assistant.retrieval.embeddings import SparseQueryEmbeddingProvider
from knowledge_assistant.storage.protocol import VectorStore


class SparseRetriever:
    """Orchestrates query sparse embedding and sparse vector search."""

    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedding_provider: SparseQueryEmbeddingProvider,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        """Embed the query text, search sparse vectors, and return ranked results."""
        sparse_vector = self._embedding_provider.embed_query(query.text)

        search_results = self._vector_store.search_sparse(
            indices=sparse_vector.indices,
            values=sparse_vector.values,
            top_k=query.top_k,
        )
        if len(search_results) > query.top_k:
            search_results = search_results[: query.top_k]

        return RetrievalResult(query=query, results=search_results)
