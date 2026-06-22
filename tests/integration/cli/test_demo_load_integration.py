"""Integration tests for rag demo load."""

import pytest

from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.cli.main import main


class TestDemoLoadIntegration:
    def test_demo_load_indexes_fixture_corpus(
        self,
        demo_environment: DemoEnvironment,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "knowledge_assistant.cli.demo.build_demo_environment",
            lambda: demo_environment,
        )
        assert not demo_environment.collection_exists()

        exit_code = main(["demo", "load"])

        assert exit_code == 0
        assert demo_environment.collection_exists()
        assert demo_environment.collection_chunk_count() > 0
        assert (
            demo_environment.collection_chunk_count()
            >= demo_environment.corpus_document_count()
        )
