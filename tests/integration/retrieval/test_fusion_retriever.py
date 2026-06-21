"""Integration tests for FusionRetriever with fake leaf retrievers."""

from conftest import FakeRetriever

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.core.source import LineRange
from knowledge_assistant.retrieval.config import FusionRetrievalSettings
from knowledge_assistant.retrieval.fusion import FusionRetriever, reciprocal_rank_fusion

RRF_K = 60


def _make_result(chunk_id: str, score: float = 0.5) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=ChunkId(chunk_id),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Section",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text=f"text for {chunk_id}",
        ),
        score=score,
    )


class TestFusionRetrieverIntegration:
    def test_fused_ordering_matches_hand_computed_rrf(self) -> None:
        caller_query = SearchQuery(text="hybrid query", top_k=3)
        leaf_query = SearchQuery(text=caller_query.text, top_k=6)
        dense_results = (
            _make_result("chunk-b"),
            _make_result("chunk-a"),
            _make_result("chunk-c"),
        )
        sparse_results = (
            _make_result("chunk-a"),
            _make_result("chunk-c"),
            _make_result("chunk-d"),
        )
        dense_fake = FakeRetriever(
            return_value=RetrievalResult(query=leaf_query, results=dense_results),
        )
        sparse_fake = FakeRetriever(
            return_value=RetrievalResult(query=leaf_query, results=sparse_results),
        )
        retriever = FusionRetriever(
            dense_retriever=dense_fake,
            sparse_retriever=sparse_fake,
            settings=FusionRetrievalSettings(rrf_k=RRF_K, leaf_top_k_multiplier=2),
        )

        result = retriever.retrieve(caller_query)
        expected = reciprocal_rank_fusion(
            dense_results=dense_results,
            sparse_results=sparse_results,
            rrf_k=RRF_K,
        )[: caller_query.top_k]

        assert result.results == expected

    def test_leaf_top_k_recorded_on_fakes(self) -> None:
        caller_query = SearchQuery(text="leaf pool", top_k=4)
        leaf_query = SearchQuery(text=caller_query.text, top_k=8)
        empty = RetrievalResult(query=leaf_query, results=())
        dense_fake = FakeRetriever(return_value=empty)
        sparse_fake = FakeRetriever(return_value=empty)
        retriever = FusionRetriever(
            dense_retriever=dense_fake,
            sparse_retriever=sparse_fake,
            settings=FusionRetrievalSettings(leaf_top_k_multiplier=2),
        )

        retriever.retrieve(caller_query)

        assert dense_fake.last_query == leaf_query
        assert sparse_fake.last_query == leaf_query

    def test_final_result_length_lte_query_top_k(self) -> None:
        caller_query = SearchQuery(text="length bound", top_k=2)
        leaf_query = SearchQuery(text=caller_query.text, top_k=4)
        dense_results = tuple(_make_result(f"chunk-{index}") for index in range(4))
        sparse_results = tuple(_make_result(f"chunk-{index}") for index in range(4, 8))
        dense_fake = FakeRetriever(
            return_value=RetrievalResult(query=leaf_query, results=dense_results),
        )
        sparse_fake = FakeRetriever(
            return_value=RetrievalResult(query=leaf_query, results=sparse_results),
        )
        retriever = FusionRetriever(
            dense_retriever=dense_fake,
            sparse_retriever=sparse_fake,
            settings=FusionRetrievalSettings(),
        )

        result = retriever.retrieve(caller_query)

        assert len(result.results) <= caller_query.top_k
