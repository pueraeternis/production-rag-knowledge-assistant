"""Integration tests for rag evaluate run."""

import pytest

from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.cli.main import main

_INTEGRATION_BENCHMARK = (
    "tests/integration/evaluation/fixtures/minimal_eval_benchmark.json"
)


class TestEvaluateRunIntegration:
    def test_evaluate_run_exits_zero_with_indexed_fixture_corpus(
        self,
        demo_environment: DemoEnvironment,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(
            "knowledge_assistant.cli.evaluate.build_demo_environment",
            lambda: demo_environment,
        )
        demo_environment.indexing_pipeline.index_documents(
            (demo_environment.corpus_indexing_source(),),
            rebuild=False,
        )

        exit_code = main(
            [
                "evaluate",
                "run",
                "--strategy",
                "dense",
                "--dataset",
                _INTEGRATION_BENCHMARK,
                "--eval-top-k",
                "3",
                "--metrics-k",
                "1,3",
            ],
        )

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Evaluation Report: dense" in captured.out
        assert "Hit@1" in captured.out
        assert "MRR:" in captured.out

    def test_evaluate_run_empty_collection_returns_exit_code_3(
        self,
        demo_environment: DemoEnvironment,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "knowledge_assistant.cli.evaluate.build_demo_environment",
            lambda: demo_environment,
        )

        exit_code = main(
            [
                "evaluate",
                "run",
                "--strategy",
                "fusion",
                "--dataset",
                _INTEGRATION_BENCHMARK,
            ],
        )

        assert exit_code == 3
