"""Argparse tests for rag evaluate subcommands."""

import pytest

from knowledge_assistant.cli.main import build_parser


class TestEvaluateParsing:
    def test_evaluate_run_parses_strategy_and_defaults(self) -> None:
        args = build_parser().parse_args(
            ["evaluate", "run", "--strategy", "dense"],
        )
        assert args.command == "evaluate"
        assert args.evaluate_command == "run"
        assert args.strategy == "dense"
        assert args.eval_top_k == 5
        assert args.metrics_k == "1,3,5"

    @pytest.mark.parametrize("strategy", ["dense", "sparse", "fusion", "rerank"])
    def test_evaluate_run_accepts_canonical_strategies(self, strategy: str) -> None:
        args = build_parser().parse_args(
            ["evaluate", "run", "--strategy", strategy],
        )
        assert args.strategy == strategy

    def test_evaluate_run_custom_dataset_and_metrics(self) -> None:
        args = build_parser().parse_args(
            [
                "evaluate",
                "run",
                "--strategy",
                "rerank",
                "--dataset",
                "tests/unit/evaluation/fixtures/minimal_dataset.json",
                "--eval-top-k",
                "10",
                "--metrics-k",
                "1,5,10",
            ],
        )
        assert args.dataset.name == "minimal_dataset.json"
        assert args.eval_top_k == 10
        assert args.metrics_k == "1,5,10"

    def test_evaluate_compare_parses_defaults(self) -> None:
        args = build_parser().parse_args(["evaluate", "compare"])
        assert args.evaluate_command == "compare"
        assert args.eval_top_k == 5
        assert args.metrics_k == "1,3,5"

    def test_evaluate_run_rejects_unknown_strategy(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["evaluate", "run", "--strategy", "hybrid"])
