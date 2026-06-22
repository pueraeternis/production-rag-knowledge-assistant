"""rag CLI entrypoint."""

from __future__ import annotations

import argparse
import sys

from knowledge_assistant.cli import demo as demo_commands


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

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
