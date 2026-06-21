"""Integration test: search_documents with composed retriever and in-memory Qdrant."""

import uuid

import pytest
from qdrant_client import QdrantClient

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.document import DocumentMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.source import LineRange
from knowledge_assistant.indexing.embeddings import sparse_placeholder_vector
from knowledge_assistant.mcp_server.config import McpServerSettings
from knowledge_assistant.mcp_server.schemas import SearchDocumentsRequest
from knowledge_assistant.mcp_server.tools import search_documents
from knowledge_assistant.retrieval.config import (
    DenseRetrievalSettings,
    FusionRetrievalSettings,
    RerankRetrievalSettings,
)
from knowledge_assistant.retrieval.dense import DenseRetriever
from knowledge_assistant.retrieval.embeddings import (
    StubQueryEmbeddingProvider,
    StubSparseQueryEmbeddingProvider,
)
from knowledge_assistant.retrieval.fusion import FusionRetriever
from knowledge_assistant.retrieval.rerank import RerankRetriever, StubReranker
from knowledge_assistant.retrieval.sparse import SparseRetriever
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.models import ChunkUpsertItem
from knowledge_assistant.storage.qdrant_store import QdrantVectorStore

_DIMENSION = 8
_CHUNK_A_TEXT = "remote work policy details"
_CHUNK_B_TEXT = "travel expense guidelines"


def _make_upsert_item(
    *,
    chunk_id: str,
    text: str,
    dense_vector: tuple[float, ...],
) -> ChunkUpsertItem:
    return ChunkUpsertItem(
        chunk=Chunk(
            chunk_id=ChunkId(chunk_id),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Overview",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text=text,
        ),
        document_metadata=DocumentMetadata(
            title="Guide",
            path="docs/guide.md",
            source_uri=None,
        ),
        dense_vector=dense_vector,
        sparse_vector=sparse_placeholder_vector(),
    )


@pytest.fixture
def composed_retriever() -> RerankRetriever:
    """Production-shaped retriever stack backed by in-memory Qdrant."""
    settings = StorageSettings(
        collection_name=f"mcp-search-integration-{uuid.uuid4()}",
        dense_vector_size=_DIMENSION,
    )
    store = QdrantVectorStore(client=QdrantClient(":memory:"), settings=settings)
    store.create_collection()

    dense_provider = StubQueryEmbeddingProvider(dimension=_DIMENSION)
    store.upsert_chunks(
        (
            _make_upsert_item(
                chunk_id=str(uuid.uuid4()),
                text=_CHUNK_A_TEXT,
                dense_vector=dense_provider.embed_query(_CHUNK_A_TEXT),
            ),
            _make_upsert_item(
                chunk_id=str(uuid.uuid4()),
                text=_CHUNK_B_TEXT,
                dense_vector=dense_provider.embed_query(_CHUNK_B_TEXT),
            ),
        ),
    )

    dense_retriever = DenseRetriever(
        vector_store=store,
        embedding_provider=dense_provider,
        settings=DenseRetrievalSettings(dense_vector_size=_DIMENSION),
    )
    sparse_retriever = SparseRetriever(
        vector_store=store,
        embedding_provider=StubSparseQueryEmbeddingProvider(),
    )
    fusion_retriever = FusionRetriever(
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever,
        settings=FusionRetrievalSettings(),
    )
    return RerankRetriever(
        base_retriever=fusion_retriever,
        reranker=StubReranker(),
        settings=RerankRetrievalSettings(),
    )


class TestSearchDocumentsComposedRetrievalIntegration:
    def test_search_documents_returns_ranked_hits_from_real_stack(
        self,
        composed_retriever: RerankRetriever,
    ) -> None:
        request = SearchDocumentsRequest(query=_CHUNK_A_TEXT, top_k=1)

        response = search_documents(
            request,
            retriever=composed_retriever,
            settings=McpServerSettings(),
        )

        assert response.top_k == 1
        assert len(response.hits) == 1
        assert response.hits[0].text == _CHUNK_A_TEXT
        assert response.hits[0].source.document_title == "Guide"
        assert response.hits[0].source.document_path == "docs/guide.md"
