"""Source formatting tests for chat CLI."""

from knowledge_assistant.agent.turn import TurnSource
from knowledge_assistant.cli.chat import format_turn_sources


def test_format_turn_sources_renders_numbered_block() -> None:
    sources = (
        TurnSource(
            document_title="Remote Work Policy",
            document_path="policies/remote_work_policy.md",
            section_title="Work From Another Country",
            start_line=84,
            end_line=112,
        ),
    )
    rendered = format_turn_sources(sources)
    assert "Sources:" in rendered
    assert "[1] Remote Work Policy" in rendered
    assert "File: policies/remote_work_policy.md" in rendered
    assert "Section: Work From Another Country" in rendered
    assert "Lines: 84-112" in rendered


def test_format_turn_sources_returns_empty_for_no_sources() -> None:
    assert format_turn_sources(()) == ""
