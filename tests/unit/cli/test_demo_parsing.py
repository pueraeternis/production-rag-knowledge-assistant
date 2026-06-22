"""Argparse tests for rag demo subcommands."""

import pytest

from knowledge_assistant.cli.main import build_parser


class TestDemoParsing:
    def test_demo_info_parses(self) -> None:
        args = build_parser().parse_args(["demo", "info"])
        assert args.command == "demo"
        assert args.demo_command == "info"

    def test_demo_load_defaults(self) -> None:
        args = build_parser().parse_args(["demo", "load"])
        assert args.demo_command == "load"
        assert args.rebuild is False
        assert args.approved is False

    def test_demo_load_rebuild_and_approve_flags(self) -> None:
        args = build_parser().parse_args(["demo", "load", "--rebuild", "--approve"])
        assert args.rebuild is True
        assert args.approved is True

    def test_demo_load_yes_alias_for_approve(self) -> None:
        args = build_parser().parse_args(["demo", "load", "--rebuild", "--yes"])
        assert args.approved is True

    def test_demo_reset_requires_explicit_approve_flag(self) -> None:
        args = build_parser().parse_args(["demo", "reset", "--approve"])
        assert args.demo_command == "reset"
        assert args.approved is True

    def test_demo_reset_rejects_unknown_flags(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["demo", "reset", "--rebuild"])
