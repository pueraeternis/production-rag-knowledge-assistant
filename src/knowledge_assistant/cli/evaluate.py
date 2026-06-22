"""Evaluate command orchestration for the rag CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from knowledge_assistant.bootstrap import (
    CANONICAL_STRATEGIES,
    RetrievalStrategy,
    build_demo_environment,
    build_retriever_for_strategy,
)
from knowledge_assistant.evaluation import (
    EvaluationReport,
    EvaluationRunner,
    EvaluationSettings,
    compare_evaluation_reports,
    format_comparison_report,
    format_evaluation_report,
    load_evaluation_dataset,
)

if TYPE_CHECKING:
    from knowledge_assistant.bootstrap import DemoEnvironment
    from knowledge_assistant.evaluation import EvaluationDataset

DEFAULT_BENCHMARK_PATH = Path("data/evaluation/retrieval_benchmark_v1.json")


def _parse_metrics_k(value: str) -> tuple[int, ...]:
    parts = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not parts:
        msg = "metrics-k must contain at least one integer"
        raise ValueError(msg)
    return parts


def _build_evaluation_settings(
    *,
    eval_top_k: int,
    metrics_k_raw: str,
) -> EvaluationSettings:
    return EvaluationSettings(
        eval_top_k=eval_top_k,
        metrics_k=_parse_metrics_k(metrics_k_raw),
    )


def _validate_preconditions(
    environment: DemoEnvironment,
    dataset_path: Path,
) -> int | None:
    if not dataset_path.is_file():
        print(
            f"error: benchmark dataset not found: {dataset_path.resolve()}",
            file=sys.stderr,
        )
        return 3

    if not environment.collection_exists():
        print(
            "error: collection does not exist; run `rag demo load` first",
            file=sys.stderr,
        )
        return 3

    if environment.collection_chunk_count() == 0:
        print(
            "error: collection is empty; run `rag demo load` first",
            file=sys.stderr,
        )
        return 3

    return None


def _print_configuration_banner(
    environment: DemoEnvironment,
    dataset: EvaluationDataset,
    settings: EvaluationSettings,
) -> None:
    embedding_mode = environment.settings.embedding_mode
    reranker_mode = environment.settings.reranker_mode
    metrics_k_display = ",".join(str(k) for k in settings.metrics_k)

    print("Evaluation configuration:")
    print(f"  Dataset: {dataset.dataset_id}")
    print(f"  Cases: {len(dataset.cases)}")
    print(f"  Eval top_k: {settings.eval_top_k}")
    print(f"  Metrics k: {metrics_k_display}")
    print(f"  Embedding mode: {embedding_mode}")
    print(f"  Reranker mode: {reranker_mode}")
    print(f"  Collection: {environment.settings.collection_name}")
    print(f"  Collection chunks: {environment.collection_chunk_count()}")
    print(f"  Pipeline: {environment.pipeline_label}")

    if embedding_mode == "stub" or reranker_mode == "stub":
        print(
            "  Note: stub provider mode — results verify wiring and relative "
            "strategy behavior, not authoritative model-quality benchmarks.",
        )
    print()


def run_evaluate_run(
    *,
    strategy: RetrievalStrategy,
    dataset_path: Path = DEFAULT_BENCHMARK_PATH,
    eval_top_k: int = 5,
    metrics_k: str = "1,3,5",
) -> int:
    """Evaluate one retrieval strategy against the benchmark."""
    try:
        settings = _build_evaluation_settings(
            eval_top_k=eval_top_k,
            metrics_k_raw=metrics_k,
        )
    except ValueError as exc:
        print(f"error: invalid evaluation settings: {exc}", file=sys.stderr)
        return 2

    try:
        environment = build_demo_environment()
    except Exception as exc:
        print(f"error: failed to assemble demo environment: {exc}", file=sys.stderr)
        return 1

    precondition_exit = _validate_preconditions(environment, dataset_path)
    if precondition_exit is not None:
        return precondition_exit

    try:
        dataset = load_evaluation_dataset(dataset_path)
    except Exception as exc:
        print(f"error: failed to load benchmark dataset: {exc}", file=sys.stderr)
        return 1

    try:
        retriever = build_retriever_for_strategy(environment, strategy)
        runner = EvaluationRunner(settings=settings)
        report = runner.run(
            retriever,
            dataset,
            retriever_label=strategy,
        )
    except Exception as exc:
        print(f"error: evaluation failed: {exc}", file=sys.stderr)
        return 1

    _print_configuration_banner(environment, dataset, settings)
    print(format_evaluation_report(report))
    return 0


def run_evaluate_compare(
    *,
    dataset_path: Path = DEFAULT_BENCHMARK_PATH,
    eval_top_k: int = 5,
    metrics_k: str = "1,3,5",
) -> int:
    """Evaluate all canonical strategies and print a comparison report."""
    try:
        settings = _build_evaluation_settings(
            eval_top_k=eval_top_k,
            metrics_k_raw=metrics_k,
        )
    except ValueError as exc:
        print(f"error: invalid evaluation settings: {exc}", file=sys.stderr)
        return 2

    try:
        environment = build_demo_environment()
    except Exception as exc:
        print(f"error: failed to assemble demo environment: {exc}", file=sys.stderr)
        return 1

    precondition_exit = _validate_preconditions(environment, dataset_path)
    if precondition_exit is not None:
        return precondition_exit

    try:
        dataset = load_evaluation_dataset(dataset_path)
    except Exception as exc:
        print(f"error: failed to load benchmark dataset: {exc}", file=sys.stderr)
        return 1

    runner = EvaluationRunner(settings=settings)
    reports: list[EvaluationReport] = []
    try:
        for strategy in CANONICAL_STRATEGIES:
            print(f"Evaluating strategy: {strategy}", file=sys.stderr)
            retriever = build_retriever_for_strategy(environment, strategy)
            reports.append(
                runner.run(
                    retriever,
                    dataset,
                    retriever_label=strategy,
                ),
            )
        comparison = compare_evaluation_reports(tuple(reports))
    except Exception as exc:
        print(f"error: evaluation comparison failed: {exc}", file=sys.stderr)
        return 1

    _print_configuration_banner(environment, dataset, settings)
    print(format_comparison_report(comparison))
    return 0


__all__ = (
    "CANONICAL_STRATEGIES",
    "DEFAULT_BENCHMARK_PATH",
    "run_evaluate_compare",
    "run_evaluate_run",
)
