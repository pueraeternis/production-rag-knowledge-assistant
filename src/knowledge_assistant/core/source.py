"""Source attribution value objects."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LineRange:
    """Inclusive 1-based line span within a source document."""

    start_line: int
    end_line: int

    def __post_init__(self) -> None:
        if self.start_line < 1:
            msg = "start_line must be >= 1"
            raise ValueError(msg)
        if self.end_line < self.start_line:
            msg = "end_line must be >= start_line"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Canonical citation model for answer grounding and user-visible attribution."""

    document_title: str
    document_path: str
    section_title: str
    line_range: LineRange

    def __post_init__(self) -> None:
        if not self.document_title.strip():
            msg = "document_title must be non-empty"
            raise ValueError(msg)
        if not self.document_path.strip():
            msg = "document_path must be non-empty"
            raise ValueError(msg)
