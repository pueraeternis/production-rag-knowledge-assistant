"""rag CLI entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from knowledge_assistant.cli import chat as chat_commands
from knowledge_assistant.cli import demo as demo_commands
from knowledge_assistant.cli import evaluate as evaluate_commands


def _add_evaluate_shared_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dataset",
        type=Path,
        default=evaluate_commands.DEFAULT_BENCHMARK_PATH,
        help="benchmark JSON path",
    )
    parser.add_argument(
        "--eval-top-k",
        type=int,
        default=5,
        help="retrieval depth for each benchmark case",
    )
    parser.add_argument(
        "--metrics-k",
        default="1,3,5",
        help="comma-separated K values for Hit Rate@K and Recall@K",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rag",
        description="RAG knowledge assistant CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser("demo", help="demo bootstrap workflow")
    demo_subparsers = demo_parser.add_subparsers(dest="demo_command", required=True)

    demo_subparsers.add_parser("info", help="show demo readiness without mutations")

    load_parser = demo_subparsers.add_parser(
        "load",
        help="index the canonical corpus into Qdrant",
    )
    load_parser.add_argument(
        "--rebuild",
        action="store_true",
        help="replace an existing collection (requires --approve)",
    )
    load_parser.add_argument(
        "--approve",
        "--yes",
        action="store_true",
        dest="approved",
        help="confirm destructive indexing operations",
    )

    reset_parser = demo_subparsers.add_parser(
        "reset",
        help="delete the demo Qdrant collection",
    )
    reset_parser.add_argument(
        "--approve",
        "--yes",
        action="store_true",
        dest="approved",
        help="confirm collection deletion",
    )

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="retrieval strategy evaluation",
    )
    evaluate_subparsers = evaluate_parser.add_subparsers(
        dest="evaluate_command",
        required=True,
    )

    run_parser = evaluate_subparsers.add_parser(
        "run",
        help="evaluate one retrieval strategy",
    )
    run_parser.add_argument(
        "--strategy",
        required=True,
        choices=evaluate_commands.CANONICAL_STRATEGIES,
        help="retrieval strategy to evaluate",
    )
    _add_evaluate_shared_options(run_parser)

    compare_parser = evaluate_subparsers.add_parser(
        "compare",
        help="evaluate all canonical strategies and compare",
    )
    _add_evaluate_shared_options(compare_parser)

    chat_parser = subparsers.add_parser("chat", help="interactive streaming chat")
    chat_parser.add_argument(
        "--message",
        help="run a single turn and exit",
    )
    chat_parser.add_argument(
        "--no-stream",
        action="store_true",
        help="disable streaming and print the full answer at once",
    )
    chat_parser.add_argument(
        "--no-sources",
        action="store_true",
        help="omit the post-turn Sources block",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        if args.demo_command == "info":
            return demo_commands.run_demo_info()
        if args.demo_command == "load":
            return demo_commands.run_demo_load(
                rebuild=args.rebuild,
                approved=args.approved,
            )
        if args.demo_command == "reset":
            return demo_commands.run_demo_reset(approved=args.approved)

    if args.command == "evaluate":
        if args.evaluate_command == "run":
            return evaluate_commands.run_evaluate_run(
                strategy=args.strategy,
                dataset_path=args.dataset,
                eval_top_k=args.eval_top_k,
                metrics_k=args.metrics_k,
            )
        if args.evaluate_command == "compare":
            return evaluate_commands.run_evaluate_compare(
                dataset_path=args.dataset,
                eval_top_k=args.eval_top_k,
                metrics_k=args.metrics_k,
            )

    if args.command == "chat":
        return chat_commands.run_chat(
            message=args.message,
            stream=not args.no_stream,
            show_sources=not args.no_sources,
        )

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
