"""Metrics helpers for generated corpus quality gates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class QualityIssue:
    """One quality gate violation."""

    path: str
    message: str


@dataclass(slots=True)
class DocumentMetrics:
    """Per-document quality metrics."""

    path: str
    word_count: int
    section_titles: tuple[str, ...]
    paragraph_count: int
    duplicate_paragraphs: int
    duplicate_sentences: int
    repeated_sentence_ratio: float
    section_diversity: float
    filler_hits: int


@dataclass(slots=True)
class CorpusMetrics:
    """Corpus-level quality metrics."""

    documents: int = 0
    duplicate_paragraphs: int = 0
    duplicate_sentences: int = 0
    avg_repeated_sentence_ratio: float = 0.0
    avg_section_diversity: float = 0.0
    distinct_section_structures: int = 0
    filler_hits: int = 0
    per_doc: list[DocumentMetrics] = field(default_factory=list)


def body_text(markdown: str) -> str:
    """Return Markdown content without YAML front matter."""
    if markdown.startswith("---"):
        return markdown.split("---", 2)[-1]
    return markdown


def word_count(text: str) -> int:
    """Count words in text."""
    return len(re.findall(r"\b\w+\b", text))


def paragraphs(text: str) -> list[str]:
    """Extract prose paragraphs used by duplication gates."""
    blocks: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        cleaned = block.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        if cleaned.startswith(("|", "* ", "- ")):
            continue
        blocks.append(cleaned)
    return blocks


def sentences(text: str) -> list[str]:
    """Extract sentence-like spans."""
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", text.strip())
        if len(part.strip()) > 20
    ]


def section_titles(text: str) -> tuple[str, ...]:
    """Return second-level Markdown headings."""
    return tuple(
        match.group(1).strip()
        for match in re.finditer(r"^##\s+(.+)$", text, flags=re.MULTILINE)
    )
