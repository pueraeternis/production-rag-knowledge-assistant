"""Integration tests for SparseRetriever with a fake VectorStore."""

from conftest import CountingSparseQueryEmbeddingProvider, FakeVectorStore

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import SearchQuery, SearchResult
from knowledge_assistant.core.source import LineRange
from knowledge_assistant.retrieval.embeddings import StubSparseQueryEmbeddingProvider
from knowledge_assistant.retrieval.sparse import SparseRetriever


def _make_search_result(
    chunk_id: str = "chunk-1",
    score: float = 0.9,
) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=ChunkId(chunk_id),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Section",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text="chunk text",
        ),
        score=score,
    )


class TestSparseRetrieverIntegration:
    def test_retrieve_invokes_embed_query_once(
        self,
        fake_vector_store: FakeVectorStore,
    ) -> None:
        provider = CountingSparseQueryEmbeddingProvider()
        retriever = SparseRetriever(
            vector_store=fake_vector_store,
            embedding_provider=provider,
        )
        query = SearchQuery(text="integration sparse query", top_k=3)

        retriever.retrieve(query)

        assert provider.embed_query_call_count == 1

    def test_retrieve_forwards_sparse_vector_and_top_k(
        self,
        fake_vector_store: FakeVectorStore,
    ) -> None:
        provider = StubSparseQueryEmbeddingProvider()
        retriever = SparseRetriever(
            vector_store=fake_vector_store,
            embedding_provider=provider,
        )
        query = SearchQuery(text="forward sparse vector", top_k=4)
        expected_vector = provider.embed_query(query.text)

        retriever.retrieve(query)

        assert fake_vector_store.last_sparse_indices == expected_vector.indices
        assert fake_vector_store.last_sparse_values == expected_vector.values
        assert fake_vector_store.last_sparse_top_k == 4

    def test_retrieve_propagates_fake_store_results(
        self,
        fake_vector_store: FakeVectorStore,
    ) -> None:
        expected_results = (
            _make_search_result("chunk-1", score=0.91),
            _make_search_result("chunk-2", score=0.82),
        )
        fake_vector_store.sparse_search_results = expected_results
        provider = StubSparseQueryEmbeddingProvider()
        retriever = SparseRetriever(
            vector_store=fake_vector_store,
            embedding_provider=provider,
        )
        query = SearchQuery(text="result propagation", top_k=2)

        result = retriever.retrieve(query)

        assert result.results == expected_results

    def test_retrieve_handles_empty_fake_store_results(
        self,
        fake_vector_store: FakeVectorStore,
    ) -> None:
        provider = StubSparseQueryEmbeddingProvider()
        retriever = SparseRetriever(
            vector_store=fake_vector_store,
            embedding_provider=provider,
        )
        query = SearchQuery(text="empty sparse results", top_k=3)

        result = retriever.retrieve(query)

        assert result.results == ()
        assert result.query == query
