"""Retrieval wiring smoke test after demo load."""

from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.core.retrieval import SearchQuery


class TestDemoRetrievalSmoke:
    def test_fixture_corpus_retrieval_returns_results_after_load(
        self,
        demo_environment: DemoEnvironment,
    ) -> None:
        demo_environment.indexing_pipeline.index_documents(
            (demo_environment.corpus_indexing_source(),),
            rebuild=False,
        )

        result = demo_environment.retriever.retrieve(
            SearchQuery(text="remote work policy", top_k=3),
        )

        assert len(result.results) >= 1
