"""Integration tests for RerankRetriever with fake base retriever."""

from conftest import FakeRetriever

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.retrieval.config import RerankRetrievalSettings
from knowledge_assistant.retrieval.rerank import (
    RerankRetriever,
    StubReranker,
    stub_rerank_score,
)


def _make_source() -> SourceReference:
    return SourceReference(
        document_title="Guide",
        document_path="docs/guide.md",
        section_title="Section",
        line_range=LineRange(start_line=1, end_line=5),
    )


def _make_result(chunk_id: str, score: float, *, text: str) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            chunk_id=ChunkId(chunk_id),
            metadata=ChunkMetadata(
                document_id=DocumentId("doc-1"),
                section_title="Section",
                line_range=LineRange(start_line=1, end_line=5),
                chunk_index=0,
            ),
            text=text,
        ),
        score=score,
        source=_make_source(),
    )


class TestRerankRetrieverIntegration:
    def test_reranked_ordering_differs_from_base_when_stub_dictates(self) -> None:
        caller_query = SearchQuery(text="python retrieval", top_k=2)
        candidate_query = SearchQuery(text=caller_query.text, top_k=4)
        base_results = (
            _make_result("chunk-low", 0.99, text="unrelated content"),
            _make_result("chunk-high", 0.01, text="python retrieval guide"),
            _make_result("chunk-mid", 0.5, text="python notes"),
            _make_result("chunk-tail", 0.2, text="other topic"),
        )
        base_fake = FakeRetriever(
            return_value=RetrievalResult(query=candidate_query, results=base_results),
        )
        retriever = RerankRetriever(
            base_retriever=base_fake,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(candidate_top_k_multiplier=2),
        )

        result = retriever.retrieve(caller_query)

        assert [item.chunk.chunk_id for item in base_results[:2]] == [
            ChunkId("chunk-low"),
            ChunkId("chunk-high"),
        ]
        assert result.results[0].chunk.chunk_id == ChunkId("chunk-high")

    def test_candidate_top_k_recorded_on_fake(self) -> None:
        caller_query = SearchQuery(text="candidate pool", top_k=4)
        candidate_query = SearchQuery(text=caller_query.text, top_k=8)
        base_fake = FakeRetriever(
            return_value=RetrievalResult(query=candidate_query, results=()),
        )
        retriever = RerankRetriever(
            base_retriever=base_fake,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(candidate_top_k_multiplier=2),
        )

        retriever.retrieve(caller_query)

        assert base_fake.last_query == candidate_query

    def test_final_result_length_lte_query_top_k(self) -> None:
        caller_query = SearchQuery(text="length bound", top_k=2)
        candidate_query = SearchQuery(text=caller_query.text, top_k=4)
        base_results = tuple(
            _make_result(f"chunk-{index}", 0.1 * index, text=f"length bound {index}")
            for index in range(4)
        )
        base_fake = FakeRetriever(
            return_value=RetrievalResult(query=candidate_query, results=base_results),
        )
        retriever = RerankRetriever(
            base_retriever=base_fake,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(),
        )

        result = retriever.retrieve(caller_query)

        assert len(result.results) <= caller_query.top_k

    def test_scores_match_stub_reranker_expectations(self) -> None:
        caller_query = SearchQuery(text="python retrieval", top_k=2)
        candidate_query = SearchQuery(text=caller_query.text, top_k=4)
        base_results = (
            _make_result("chunk-a", 0.9, text="python retrieval alpha"),
            _make_result("chunk-b", 0.8, text="python retrieval beta"),
        )
        base_fake = FakeRetriever(
            return_value=RetrievalResult(query=candidate_query, results=base_results),
        )
        retriever = RerankRetriever(
            base_retriever=base_fake,
            reranker=StubReranker(),
            settings=RerankRetrievalSettings(candidate_top_k_multiplier=2),
        )

        result = retriever.retrieve(caller_query)

        for item in result.results:
            expected = stub_rerank_score(caller_query.text, item.chunk.text)
            assert item.score == expected
