"""Unit tests for reranking settings and StubReranker."""

import pytest

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.retrieval import SearchQuery, SearchResult
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.retrieval.config import (
    BgeRerankerSettings,
    RerankRetrievalSettings,
)
from knowledge_assistant.retrieval.rerank import (
    BgeReranker,
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


def _make_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=ChunkId(chunk_id),
        metadata=ChunkMetadata(
            document_id=DocumentId("doc-1"),
            section_title="Section",
            line_range=LineRange(start_line=1, end_line=5),
            chunk_index=0,
        ),
        text=text,
    )


def _make_result(
    chunk_id: str,
    score: float,
    *,
    text: str | None = None,
) -> SearchResult:
    return SearchResult(
        chunk=_make_chunk(
            chunk_id,
            text if text is not None else f"text for {chunk_id}",
        ),
        score=score,
        source=_make_source(),
    )


class TestRerankRetrievalSettings:
    def test_default_candidate_top_k_multiplier(self) -> None:
        settings = RerankRetrievalSettings()
        assert settings.candidate_top_k_multiplier == 2

    def test_resolve_candidate_top_k(self) -> None:
        settings = RerankRetrievalSettings()
        assert settings.resolve_candidate_top_k(5) == 10

    @pytest.mark.parametrize("candidate_top_k_multiplier", [0, -1])
    def test_candidate_top_k_multiplier_must_be_at_least_one(
        self,
        candidate_top_k_multiplier: int,
    ) -> None:
        with pytest.raises(ValueError, match="candidate_top_k_multiplier must be >= 1"):
            RerankRetrievalSettings(
                candidate_top_k_multiplier=candidate_top_k_multiplier,
            )


class TestStubReranker:
    def test_empty_candidates_returns_empty_tuple(self) -> None:
        query = SearchQuery(text="empty candidates", top_k=3)
        reranker = StubReranker()

        assert reranker.rerank(query, ()) == ()

    def test_preserves_candidate_count(self) -> None:
        query = SearchQuery(text="python retrieval", top_k=2)
        candidates = (
            _make_result("chunk-a", 0.9, text="python guide"),
            _make_result("chunk-b", 0.1, text="unrelated topic"),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert len(reranked) == len(candidates)

    def test_preserves_source_reference(self) -> None:
        query = SearchQuery(text="python retrieval", top_k=2)
        source = SourceReference(
            document_title="Guide",
            document_path="docs/guide.md",
            section_title="Overview",
            line_range=LineRange(start_line=3, end_line=9),
        )
        candidates = (
            SearchResult(
                chunk=_make_chunk("chunk-a", "python guide"),
                score=0.9,
                source=source,
            ),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert reranked[0].source == source

    def test_deterministic_scores_for_same_inputs(self) -> None:
        query = SearchQuery(text="hybrid search fusion", top_k=3)
        candidates = (
            _make_result("chunk-a", 0.5, text="hybrid search overview"),
            _make_result("chunk-b", 0.8, text="fusion retrieval notes"),
        )
        reranker = StubReranker()

        first = reranker.rerank(query, candidates)
        second = reranker.rerank(query, candidates)

        assert first == second

    def test_higher_overlap_candidate_sorts_first(self) -> None:
        query = SearchQuery(text="python retrieval", top_k=2)
        candidates = (
            _make_result("chunk-low", 0.99, text="unrelated content"),
            _make_result("chunk-high", 0.01, text="python retrieval guide"),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert reranked[0].chunk.chunk_id == ChunkId("chunk-high")
        assert reranked[0].score > reranked[1].score

    def test_reranked_score_replaces_input_score(self) -> None:
        query = SearchQuery(text="python", top_k=1)
        prior_score = 0.42
        candidates = (_make_result("chunk-a", prior_score, text="python basics"),)
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert reranked[0].score == pytest.approx(
            stub_rerank_score("python", "python basics"),
        )
        assert reranked[0].score != prior_score

    def test_tie_on_reranker_score_orders_by_chunk_id_ascending(self) -> None:
        query = SearchQuery(text="shared overlap", top_k=3)
        shared_text = "shared overlap text"
        candidates = (
            _make_result("chunk-b", 0.5, text=shared_text),
            _make_result("chunk-a", 0.5, text=shared_text),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert reranked[0].chunk.chunk_id == ChunkId("chunk-a")
        assert reranked[1].chunk.chunk_id == ChunkId("chunk-b")
        assert reranked[0].score == pytest.approx(reranked[1].score)

    def test_every_chunk_id_appears_exactly_once(self) -> None:
        query = SearchQuery(text="token overlap", top_k=3)
        candidates = (
            _make_result("chunk-a", 0.1, text="token overlap alpha"),
            _make_result("chunk-b", 0.2, text="token overlap beta"),
            _make_result("chunk-c", 0.3, text="token overlap gamma"),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)
        input_ids = {candidate.chunk.chunk_id for candidate in candidates}
        output_ids = [result.chunk.chunk_id for result in reranked]

        assert len(output_ids) == len(set(output_ids))
        assert set(output_ids) == input_ids

    def test_chunk_payloads_unchanged(self) -> None:
        query = SearchQuery(text="preserve payload", top_k=2)
        candidates = (
            _make_result("chunk-a", 0.5, text="preserve payload alpha"),
            _make_result("chunk-b", 0.4, text="preserve payload beta"),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        for original in candidates:
            matching = next(
                result
                for result in reranked
                if result.chunk.chunk_id == original.chunk.chunk_id
            )
            assert matching.chunk == original.chunk

    def test_tokenization_ignores_trailing_punctuation(self) -> None:
        query = SearchQuery(text="python retrieval", top_k=2)
        candidates = (
            _make_result("chunk-plain", 0.1, text="python retrieval guide"),
            _make_result("chunk-punct", 0.9, text="python retrieval, guide"),
        )
        reranker = StubReranker()

        reranked = reranker.rerank(query, candidates)

        assert reranked[0].score == pytest.approx(reranked[1].score)
        assert stub_rerank_score(
            "python retrieval", "python retrieval,"
        ) == pytest.approx(
            stub_rerank_score("python retrieval", "python retrieval"),
        )


class FakeBgeBackend:
    def __init__(self, scores: list[float]) -> None:
        self._scores = scores
        self.calls: list[list[tuple[str, str]]] = []
        self.batch_sizes: list[int] = []
        self.max_lengths: list[int] = []

    def compute_scores(
        self,
        pairs: list[tuple[str, str]],
        *,
        batch_size: int,
        max_length: int,
    ) -> list[float]:
        self.calls.append(pairs)
        self.batch_sizes.append(batch_size)
        self.max_lengths.append(max_length)
        return self._scores


class CountingLoader:
    def __init__(self, backend: FakeBgeBackend) -> None:
        self.backend = backend
        self.call_count = 0
        self.settings_seen: list[BgeRerankerSettings] = []

    def __call__(self, settings: BgeRerankerSettings) -> FakeBgeBackend:
        self.call_count += 1
        self.settings_seen.append(settings)
        return self.backend


class TestBgeReranker:
    def test_empty_candidates_returns_empty_without_loading_model(self) -> None:
        backend = FakeBgeBackend(scores=[])
        loader = CountingLoader(backend)
        reranker = BgeReranker(
            settings=BgeRerankerSettings(),
            model_loader=loader,
        )

        result = reranker.rerank(SearchQuery(text="anything", top_k=3), ())

        assert result == ()
        assert loader.call_count == 0

    def test_model_loads_lazily_and_is_reused(self) -> None:
        backend = FakeBgeBackend(scores=[0.7])
        loader = CountingLoader(backend)
        settings = BgeRerankerSettings(batch_size=4, max_length=128)
        reranker = BgeReranker(settings=settings, model_loader=loader)
        candidates = (_make_result("chunk-a", 0.1, text="alpha"),)

        first = reranker.rerank(SearchQuery(text="query", top_k=1), candidates)
        second = reranker.rerank(SearchQuery(text="query", top_k=1), candidates)

        assert first == second
        assert loader.call_count == 1
        assert loader.settings_seen == [settings]
        assert backend.batch_sizes == [4, 4]
        assert backend.max_lengths == [128, 128]

    def test_passes_one_query_chunk_pair_per_candidate(self) -> None:
        backend = FakeBgeBackend(scores=[0.1, 0.2])
        loader = CountingLoader(backend)
        reranker = BgeReranker(
            settings=BgeRerankerSettings(),
            model_loader=loader,
        )
        query = SearchQuery(text="policy question", top_k=2)
        candidates = (
            _make_result("chunk-a", 0.9, text="first text"),
            _make_result("chunk-b", 0.8, text="second text"),
        )

        reranker.rerank(query, candidates)

        assert backend.calls == [
            [("policy question", "first text"), ("policy question", "second text")],
        ]

    def test_backend_score_count_mismatch_raises_value_error(self) -> None:
        backend = FakeBgeBackend(scores=[0.5])
        loader = CountingLoader(backend)
        reranker = BgeReranker(
            settings=BgeRerankerSettings(),
            model_loader=loader,
        )
        candidates = (
            _make_result("chunk-a", 0.9, text="first"),
            _make_result("chunk-b", 0.8, text="second"),
        )

        with pytest.raises(ValueError, match="returned 1 scores for 2 candidates"):
            reranker.rerank(SearchQuery(text="query", top_k=2), candidates)

    def test_preserves_candidate_count_chunk_and_source_while_replacing_scores(
        self,
    ) -> None:
        backend = FakeBgeBackend(scores=[3.0, 1.0])
        loader = CountingLoader(backend)
        reranker = BgeReranker(
            settings=BgeRerankerSettings(),
            model_loader=loader,
        )
        candidates = (
            _make_result("chunk-a", 0.9, text="first"),
            _make_result("chunk-b", 0.8, text="second"),
        )

        reranked = reranker.rerank(SearchQuery(text="query", top_k=2), candidates)

        assert len(reranked) == len(candidates)
        assert reranked[0].chunk == candidates[0].chunk
        assert reranked[0].source == candidates[0].source
        assert reranked[0].score == 3.0
        assert reranked[1].chunk == candidates[1].chunk
        assert reranked[1].source == candidates[1].source
        assert reranked[1].score == 1.0

    def test_orders_by_score_descending_then_chunk_id_ascending(self) -> None:
        backend = FakeBgeBackend(scores=[1.0, 2.0, 2.0])
        loader = CountingLoader(backend)
        reranker = BgeReranker(
            settings=BgeRerankerSettings(),
            model_loader=loader,
        )
        candidates = (
            _make_result("chunk-c", 0.9, text="third"),
            _make_result("chunk-b", 0.8, text="second"),
            _make_result("chunk-a", 0.7, text="first"),
        )

        reranked = reranker.rerank(SearchQuery(text="query", top_k=3), candidates)

        assert [result.chunk.chunk_id for result in reranked] == [
            ChunkId("chunk-a"),
            ChunkId("chunk-b"),
            ChunkId("chunk-c"),
        ]

    def test_repeated_calls_with_same_backend_scores_are_deterministic(self) -> None:
        backend = FakeBgeBackend(scores=[0.4, 0.9])
        loader = CountingLoader(backend)
        reranker = BgeReranker(
            settings=BgeRerankerSettings(),
            model_loader=loader,
        )
        candidates = (
            _make_result("chunk-a", 0.1, text="alpha"),
            _make_result("chunk-b", 0.2, text="beta"),
        )

        first = reranker.rerank(SearchQuery(text="query", top_k=2), candidates)
        second = reranker.rerank(SearchQuery(text="query", top_k=2), candidates)

        assert first == second
