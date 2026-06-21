"""Unit tests for source attribution value objects."""

from dataclasses import FrozenInstanceError

import pytest

from knowledge_assistant.core.source import LineRange, SourceReference


class TestLineRange:
    def test_valid_construction(self) -> None:
        line_range = LineRange(start_line=1, end_line=10)
        assert line_range.start_line == 1
        assert line_range.end_line == 10

    @pytest.mark.parametrize(
        ("start_line", "end_line"),
        [
            (0, 5),
            (-1, 5),
        ],
    )
    def test_start_line_must_be_at_least_one(
        self,
        start_line: int,
        end_line: int,
    ) -> None:
        with pytest.raises(ValueError, match="start_line must be >= 1"):
            LineRange(start_line=start_line, end_line=end_line)

    def test_end_line_must_be_at_least_start_line(self) -> None:
        with pytest.raises(ValueError, match="end_line must be >= start_line"):
            LineRange(start_line=5, end_line=3)

    def test_immutability(self) -> None:
        line_range = LineRange(start_line=1, end_line=5)
        with pytest.raises(FrozenInstanceError):
            line_range.start_line = 2  # type: ignore[misc]


class TestSourceReference:
    @pytest.fixture
    def line_range(self) -> LineRange:
        return LineRange(start_line=1, end_line=5)

    def test_valid_construction(self, line_range: LineRange) -> None:
        ref = SourceReference(
            document_title="Architecture Guide",
            document_path="docs/ARCHITECTURE.md",
            section_title="Overview",
            line_range=line_range,
        )
        assert ref.document_title == "Architecture Guide"
        assert ref.document_path == "docs/ARCHITECTURE.md"
        assert ref.section_title == "Overview"
        assert ref.line_range == line_range

    @pytest.mark.parametrize(
        "field_name",
        ["document_title", "document_path"],
    )
    def test_required_string_fields_must_be_non_empty(
        self,
        line_range: LineRange,
        field_name: str,
    ) -> None:
        values = {
            "document_title": "Title",
            "document_path": "path.md",
            "section_title": "",
            "line_range": line_range,
        }
        values[field_name] = "   "
        with pytest.raises(ValueError, match="must be non-empty"):
            SourceReference(**values)  # type: ignore[arg-type]

    def test_immutability(self, line_range: LineRange) -> None:
        ref = SourceReference(
            document_title="Title",
            document_path="path.md",
            section_title="",
            line_range=line_range,
        )
        with pytest.raises(FrozenInstanceError):
            ref.document_title = "Other"  # type: ignore[misc]
