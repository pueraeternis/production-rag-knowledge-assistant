"""Integration tests for DenseRetriever with a fake VectorStore."""

from conftest import CountingQueryEmbeddingProvider, FakeVectorStore

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import SearchQuery, SearchResult
from knowledge_assistant.core.source import LineRange
from knowledge_assistant.retrieval.config import DenseRetrievalSettings
from knowledge_assistant.retrieval.dense import DenseRetriever
from knowledge_assistant.retrieval.embeddings import StubQueryEmbeddingProvider


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


class TestDenseRetrieverIntegration:
    def test_retrieve_invokes_embed_query_once(
        self,
        fake_vector_store: FakeVectorStore,
    ) -> None:
        provider = CountingQueryEmbeddingProvider(dimension=8)
        retriever = DenseRetriever(
            vector_store=fake_vector_store,
            embedding_provider=provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="integration query", top_k=3)

        retriever.retrieve(query)

        assert provider.embed_query_call_count == 1

    def test_retrieve_invokes_search_dense_with_matching_vector_length(
        self,
        fake_vector_store: FakeVectorStore,
    ) -> None:
        provider = StubQueryEmbeddingProvider(dimension=8)
        retriever = DenseRetriever(
            vector_store=fake_vector_store,
            embedding_provider=provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="vector length query", top_k=3)
        expected_vector = provider.embed_query(query.text)

        retriever.retrieve(query)

        assert fake_vector_store.last_vector is not None
        assert len(fake_vector_store.last_vector) == 8
        assert fake_vector_store.last_vector == expected_vector

    def test_retrieve_forwards_top_k_to_search_dense(
        self,
        fake_vector_store: FakeVectorStore,
    ) -> None:
        provider = StubQueryEmbeddingProvider(dimension=8)
        retriever = DenseRetriever(
            vector_store=fake_vector_store,
            embedding_provider=provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="top k forwarding", top_k=4)

        retriever.retrieve(query)

        assert fake_vector_store.last_top_k == 4

    def test_retrieve_propagates_fake_store_results(
        self,
        fake_vector_store: FakeVectorStore,
    ) -> None:
        expected_results = (
            _make_search_result("chunk-1", score=0.91),
            _make_search_result("chunk-2", score=0.82),
        )
        fake_vector_store.search_results = expected_results
        provider = StubQueryEmbeddingProvider(dimension=8)
        retriever = DenseRetriever(
            vector_store=fake_vector_store,
            embedding_provider=provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="result propagation", top_k=2)

        result = retriever.retrieve(query)

        assert result.results == expected_results

    def test_retrieve_handles_empty_fake_store_results(
        self,
        fake_vector_store: FakeVectorStore,
    ) -> None:
        provider = StubQueryEmbeddingProvider(dimension=8)
        retriever = DenseRetriever(
            vector_store=fake_vector_store,
            embedding_provider=provider,
            settings=DenseRetrievalSettings(dense_vector_size=8),
        )
        query = SearchQuery(text="empty results", top_k=3)

        result = retriever.retrieve(query)

        assert result.results == ()
        assert result.query == query
