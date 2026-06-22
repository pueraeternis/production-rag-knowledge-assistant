"""Precondition and success-path tests for rag evaluate commands."""

from pathlib import Path
from unittest.mock import patch

import pytest

from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.cli import evaluate as evaluate_commands


class TestEvaluatePreconditions:
    def test_missing_dataset_returns_exit_code_3(
        self,
        demo_environment: DemoEnvironment,
        tmp_path: Path,
    ) -> None:
        missing_dataset = tmp_path / "missing.json"
        with patch(
            "knowledge_assistant.cli.evaluate.build_demo_environment",
            return_value=demo_environment,
        ):
            exit_code = evaluate_commands.run_evaluate_run(
                strategy="dense",
                dataset_path=missing_dataset,
            )

        assert exit_code == 3

    def test_empty_collection_returns_exit_code_3(
        self,
        demo_environment: DemoEnvironment,
    ) -> None:
        dataset_path = Path("tests/unit/evaluation/fixtures/minimal_dataset.json")
        assert not demo_environment.collection_exists()

        with patch(
            "knowledge_assistant.cli.evaluate.build_demo_environment",
            return_value=demo_environment,
        ):
            exit_code = evaluate_commands.run_evaluate_run(
                strategy="dense",
                dataset_path=dataset_path,
            )

        assert exit_code == 3

    def test_successful_run_prints_formatter_output(
        self,
        demo_environment: DemoEnvironment,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        dataset_path = Path("tests/unit/evaluation/fixtures/minimal_dataset.json")
        demo_environment.indexing_pipeline.index_documents(
            (demo_environment.corpus_indexing_source(),),
            rebuild=False,
        )

        with patch(
            "knowledge_assistant.cli.evaluate.build_demo_environment",
            return_value=demo_environment,
        ):
            exit_code = evaluate_commands.run_evaluate_run(
                strategy="dense",
                dataset_path=dataset_path,
                eval_top_k=1,
                metrics_k="1",
            )

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Evaluation configuration:" in captured.out
        assert "Evaluation Report: dense" in captured.out
        assert "MRR:" in captured.out

    def test_invalid_metrics_k_returns_exit_code_2(self) -> None:
        exit_code = evaluate_commands.run_evaluate_run(
            strategy="dense",
            metrics_k="",
        )
        assert exit_code == 2

    def test_compare_success_prints_strategy_columns(
        self,
        demo_environment: DemoEnvironment,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        dataset_path = Path("tests/unit/evaluation/fixtures/minimal_dataset.json")
        demo_environment.indexing_pipeline.index_documents(
            (demo_environment.corpus_indexing_source(),),
            rebuild=False,
        )

        with patch(
            "knowledge_assistant.cli.evaluate.build_demo_environment",
            return_value=demo_environment,
        ):
            exit_code = evaluate_commands.run_evaluate_compare(
                dataset_path=dataset_path,
                eval_top_k=1,
                metrics_k="1",
            )

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Comparison Report:" in captured.out
        for strategy in ("dense", "sparse", "fusion", "rerank"):
            assert strategy in captured.out
