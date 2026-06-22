"""Integration tests for rag evaluate compare."""

import pytest

from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.cli.main import main

_INTEGRATION_BENCHMARK = (
    "tests/integration/evaluation/fixtures/minimal_eval_benchmark.json"
)


class TestEvaluateCompareIntegration:
    def test_evaluate_compare_prints_all_strategy_columns(
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
                "compare",
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
        assert "Comparison Report:" in captured.out
        for strategy in ("dense", "sparse", "fusion", "rerank"):
            assert strategy in captured.out
        assert "MRR" in captured.out
